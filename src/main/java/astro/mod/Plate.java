package astro.mod;

import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.phys.Vec3;

import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

/**
 * Turkish food table-ware.
 *  - Shift + right-click the TOP of a block with a Tabak / food / plated food / utensil -> it is placed there.
 *  - Right-click a placed Tabak while holding food -> the food goes on the plate.
 *  - Right-click a placed plate with food while holding Kaşık / Çatal / Bıçak (either hand) -> eating cutscene.
 *  - Left-click (or shift + right-click with an empty hand) a placed thing -> pick it back up.
 *  - In the air: Tabak in main hand + food in off hand = plated food; plated food + utensil in off hand = eating cutscene.
 * Placed things are an interaction entity (the hitbox) + item_display entities, all server-side.
 */
public final class Plate {
    private Plate() { }

    static final String TABAK = "minecraft:bowl[custom_name={text:\"Tabak\",color:\"white\",bold:true,italic:false},"
            + "lore=[{text:\"Shift + sağ tık: bloğun üstüne koy\",color:\"gray\",italic:false}],"
            + "custom_model_data={strings:[\"tabak\"]},custom_data={astro_tool:\"tabak\"}]";
    private static final String TABAK_NBT = "{id:\"minecraft:bowl\",count:1,components:{\"minecraft:custom_name\":{text:\"Tabak\",color:\"white\",bold:true,italic:false},"
            + "\"minecraft:custom_model_data\":{strings:[\"tabak\"]},\"minecraft:custom_data\":{astro_tool:\"tabak\"}}}";
    private static final String FLAT = "left_rotation:[-0.7071f,0f,0f,0.7071f],right_rotation:[0f,0f,0f,1f]";
    private static final Set<UUID> BUSY = new HashSet<>();

    // ------------------------------------------------------------------ item helpers
    private static CompoundTag tag(ItemStack s) {
        if (s == null || s.isEmpty()) return null;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd == null ? null : cd.copyTag();
    }
    private static boolean isTool(ItemStack s, String key) {
        CompoundTag t = tag(s);
        return t != null && t.getStringOr("astro_tool", "").equals(key);
    }
    private static String utensil(ItemStack s) {
        for (String k : new String[]{"kasik", "catal", "bicak"}) if (isTool(s, k)) return k;
        return null;
    }
    private static boolean isFood(ItemStack s) {
        CompoundTag t = tag(s);
        return t != null && t.contains("astro_food") && !t.contains("astro_plated");
    }
    private static boolean isPlated(ItemStack s) {
        CompoundTag t = tag(s);
        return t != null && t.contains("astro_plated");
    }
    private static boolean isAstro(ItemStack s) {
        CompoundTag t = tag(s);
        return t != null && (t.contains("astro_food") || t.contains("astro_tool"));
    }

    // ------------------------------------------------------------------ command helpers
    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }
    private static String f(double d) { return String.format(Locale.ROOT, "%.3f", d); }
    private static String xyz(Vec3 v) { return f(v.x) + " " + f(v.y) + " " + f(v.z); }
    private static String uuidArr(UUID u) {
        long m = u.getMostSignificantBits(), l = u.getLeastSignificantBits();
        return "[I;" + (int) (m >> 32) + "," + (int) m + "," + (int) (l >> 32) + "," + (int) l + "]";
    }
    private static String dim(ServerPlayer p) {
        String s = String.valueOf(p.level().dimension());
        int i = s.lastIndexOf(" / ");
        if (i >= 0) s = s.substring(i + 3);
        return s.replace("]", "").trim();
    }
    private static String in(ServerPlayer p) { return "execute in " + dim(p) + " "; }

    /** copies exactly ONE of the item in the player's main hand into an entity's "contents" slot, removing it from the hand */
    private static void moveOneFromHand(ServerPlayer p, String targetUuid) {
        ItemStack main = p.getMainHandItem();
        ItemStack one = main.copyWithCount(1);
        ItemStack rest = main.copyWithCount(main.getCount() - 1);
        p.setItemInHand(InteractionHand.MAIN_HAND, one);
        run(p.level().getServer(), "item replace entity " + targetUuid + " contents from entity " + p.getStringUUID() + " weapon.mainhand");
        p.setItemInHand(InteractionHand.MAIN_HAND, rest);
    }

    private static int[] nutritionOf(ItemStack s) {
        CompoundTag t = tag(s);
        if (t != null && t.contains("astro_plated")) return new int[]{t.getIntOr("pn", 4), Math.round(t.getFloatOr("ps", 4f))};
        FoodProperties fp = s.get(DataComponents.FOOD);
        return fp != null ? new int[]{fp.nutrition(), Math.round(fp.saturation())} : new int[]{4, 4};
    }

    private static UUID summonDisplay(ServerPlayer p, Vec3 pos, String tags, float scale, double lift) {
        UUID u = UUID.randomUUID();
        run(p.level().getServer(), in(p) + "run summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(u) + ",Tags:[\"astro_pl\"," + tags + "],"
                + "item:{id:\"minecraft:stone\",count:1},billboard:\"fixed\",teleport_duration:4,"
                + "transformation:{" + FLAT + ",translation:[0f," + lift + "f,0f],scale:[" + scale + "f," + scale + "f," + scale + "f]}}");
        return u;
    }

    private static void setName(MinecraftServer s, String uuid, String name) {
        run(s, "data merge entity " + uuid + " {CustomName:\"" + name + "\"}");
    }

    // ------------------------------------------------------------------ placing
    private static void place(ServerPlayer p, BlockPos on) {
        ItemStack main = p.getMainHandItem();
        MinecraftServer s = p.level().getServer();
        Vec3 pos = new Vec3(on.getX() + 0.5, on.getY() + 1.0, on.getZ() + 0.5);
        UUID hit = UUID.randomUUID();
        String kind;
        if (isTool(main, "tabak")) {
            UUID d = summonDisplay(p, pos, "\"astro_pl_plate\"", 0.62f, 0.02);
            moveOneFromHand(p, d.toString());
            kind = "astro:tabak";
        } else if (isPlated(main)) {
            int[] ns = nutritionOf(main);
            UUID plate = summonDisplay(p, pos, "\"astro_pl_vis\"", 0.62f, 0.02);
            run(s, "item replace entity " + plate + " contents with " + TABAK);
            UUID food = summonDisplay(p, pos, "\"astro_pl_food\"", 0.42f, 0.07);
            moveOneFromHand(p, food.toString());
            kind = "astro:plated:" + ns[0] + ":" + ns[1];
        } else {
            UUID d = summonDisplay(p, pos, "\"astro_pl_food\"", 0.5f, 0.03);
            moveOneFromHand(p, d.toString());
            kind = "astro:item";
        }
        run(s, in(p) + "run summon minecraft:interaction " + f(pos.x) + " " + f(pos.y) + " " + f(pos.z)
                + " {UUID:" + uuidArr(hit) + ",Tags:[\"astro_pl\",\"astro_pl_hit\"],width:0.55f,height:0.22f,response:1b,CustomName:\"" + kind + "\"}");
        run(s, in(p) + "run playsound minecraft:block.decorated_pot.place master @a " + xyz(pos) + " 1 1.3");
    }

    // ------------------------------------------------------------------ picking up
    private static String near(String hitUuid, String tag) {
        return "execute at " + hitUuid + " as @e[type=item_display,tag=" + tag + ",distance=..0.3,sort=nearest,limit=1] ";
    }
    private static void dropFrom(MinecraftServer s, ServerPlayer p, String hitUuid, String tag) {
        run(s, near(hitUuid, tag) + "at @s run summon minecraft:item ~ ~0.15 ~ {Tags:[\"astro_tmp_drop\"],PickupDelay:0,Item:{id:\"minecraft:stone\",count:1}}");
        run(s, near(hitUuid, tag) + "run item replace entity @e[type=item,tag=astro_tmp_drop,limit=1] contents from entity @s contents");
        run(s, "tp @e[type=item,tag=astro_tmp_drop] " + p.getStringUUID());
        run(s, "tag @e[type=item,tag=astro_tmp_drop] remove astro_tmp_drop");
    }
    private static void pickUp(ServerPlayer p, Entity hit) {
        MinecraftServer s = p.level().getServer();
        String h = hit.getStringUUID();
        if (BUSY.contains(hit.getUUID())) return;
        dropFrom(s, p, h, "astro_pl_plate");
        dropFrom(s, p, h, "astro_pl_food");
        run(s, "execute at " + h + " run kill @e[type=item_display,tag=astro_pl,distance=..0.3]");
        run(s, "kill " + h);
        run(s, "execute at " + p.getStringUUID() + " run playsound minecraft:entity.item.pickup master @a ~ ~ ~ 0.8 1");
    }

    // ------------------------------------------------------------------ food onto a placed plate
    private static void putOnPlate(ServerPlayer p, Entity hit) {
        MinecraftServer s = p.level().getServer();
        int[] ns = nutritionOf(p.getMainHandItem());
        Vec3 pos = hit.position();
        UUID food = summonDisplay(p, pos, "\"astro_pl_food\"", 0.42f, 0.07);
        moveOneFromHand(p, food.toString());
        setName(s, hit.getStringUUID(), "astro:plated:" + ns[0] + ":" + ns[1]);
        run(s, in(p) + "run playsound minecraft:block.decorated_pot.insert master @a " + xyz(pos) + " 1 1.2");
        run(s, in(p) + "run particle minecraft:happy_villager " + f(pos.x) + " " + f(pos.y + 0.2) + " " + f(pos.z) + " 0.15 0.05 0.15 0 5");
    }

    // ------------------------------------------------------------------ THE EATING CUTSCENE
    /**
     * @param anchor   uuid of the entity at the plate (interaction or temp marker)
     * @param platePos where the plate is
     * @param temp     true = hand-held meal (everything is removed at the end and the plate goes back to the inventory)
     */
    private static void cutscene(ServerPlayer p, String anchor, UUID anchorId, Vec3 platePos, String ut, int n, int sat, boolean temp) {
        MinecraftServer s = p.level().getServer();
        UUID pid = p.getUUID();
        BUSY.add(pid);
        BUSY.add(anchorId);
        String name = p.getName().getString();
        String pu = p.getStringUUID();
        Vec3 feet = p.position();
        String D = in(p);
        // camera: lock the player and make them look at the plate
        run(s, "effect give " + pu + " minecraft:slowness 4 255 true");
        run(s, D + "run tp " + pu + " " + xyz(feet) + " facing " + f(platePos.x) + " " + f(platePos.y + 0.05) + " " + f(platePos.z));
        run(s, "title " + pu + " times 5 50 10");
        run(s, "title " + pu + " title {\"text\":\"\"}");
        run(s, "title " + pu + " subtitle {\"text\":\"🍴 Afiyetle yeniyor...\",\"color\":\"gold\",\"italic\":true}");
        // the utensil that flies between the plate and your mouth
        UUID utId = UUID.randomUUID();
        String utU = utId.toString();
        Vec3 start = platePos.add(0.18, 0.08, 0);
        run(s, D + "run summon minecraft:item_display " + xyz(start) + " {UUID:" + uuidArr(utId) + ",Tags:[\"astro_pl\",\"astro_pl_ut\"],billboard:\"fixed\",teleport_duration:6,"
                + "item:{id:\"minecraft:stick\",count:1,components:{\"minecraft:custom_model_data\":{strings:[\"" + ut + "\"]}}},"
                + "transformation:{left_rotation:[0f,0f,0.3827f,0.9239f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[0.55f,0.55f,0.55f]}}");
        Vec3 look = p.getLookAngle();
        Vec3 eye = p.getEyePosition();
        Vec3 mouth = eye.add(look.scale(0.45)).add(0, -0.18, 0);
        String sound = ut.equals("kasik") ? "minecraft:entity.generic.drink" : "minecraft:entity.generic.eat";
        float[] sizes = {0.31f, 0.2f, 0.09f};
        for (int i = 0; i < 3; i++) {
            final int bite = i;
            int t0 = 8 + i * 18;
            // dip into the food
            OnePunch.later(t0, () -> {
                run(s, D + "run tp " + utU + " " + xyz(platePos.add(0.05, 0.1, 0)));
                run(s, D + "run particle minecraft:crit " + xyz(platePos.add(0, 0.12, 0)) + " 0.08 0.02 0.08 0 4");
            });
            // lift to the mouth
            OnePunch.later(t0 + 6, () -> run(s, D + "run tp " + utU + " " + xyz(mouth)));
            // BITE
            OnePunch.later(t0 + 12, () -> {
                run(s, D + "run playsound " + sound + " master @a " + xyz(mouth) + " 1 " + (0.9f + bite * 0.1f));
                run(s, D + "run particle minecraft:item_slime " + xyz(mouth) + " 0.06 0.04 0.06 0 0");
                run(s, D + "run particle minecraft:composter " + xyz(mouth) + " 0.12 0.06 0.12 0 6");
                run(s, "execute at " + anchor + " as @e[type=item_display,tag=astro_pl_food,distance=..0.3,sort=nearest,limit=1] run data merge entity @s "
                        + "{start_interpolation:0,interpolation_duration:6,transformation:{" + FLAT + ",translation:[0f,0.07f,0f],scale:["
                        + sizes[bite] + "f," + sizes[bite] + "f," + sizes[bite] + "f]}}");
                run(s, "title " + pu + " actionbar {\"text\":\"" + "😋 ".repeat(bite + 1) + "\",\"color\":\"yellow\"}");
                run(s, D + "run tp " + pu + " " + xyz(feet) + " facing " + f(platePos.x) + " " + f(platePos.y + 0.05) + " " + f(platePos.z));
            });
        }
        // finale
        OnePunch.later(8 + 3 * 18 + 4, () -> {
            run(s, "kill " + utU);
            run(s, "execute at " + anchor + " run kill @e[type=item_display,tag=astro_pl_food,distance=..0.3]");
            var fd = p.getFoodData();
            fd.setFoodLevel(Math.min(20, fd.getFoodLevel() + n + 2));
            fd.setSaturation(Math.min((float) fd.getFoodLevel(), fd.getSaturationLevel() + sat + 2f));
            run(s, "effect clear " + pu + " minecraft:slowness");
            run(s, "effect give " + pu + " minecraft:regeneration 4 0 true");
            run(s, D + "run playsound minecraft:entity.player.burp master @a " + xyz(feet) + " 1 1");
            run(s, D + "run playsound minecraft:entity.player.levelup master @a " + xyz(feet) + " 0.6 1.6");
            run(s, D + "run particle minecraft:heart " + f(feet.x) + " " + f(feet.y + 2.1) + " " + f(feet.z) + " 0.3 0.1 0.3 0 5");
            run(s, "title " + pu + " title {\"text\":\"Afiyet olsun!\",\"color\":\"gold\",\"bold\":true}");
            run(s, "title " + pu + " subtitle {\"text\":\"Eline sağlık usta 👨‍🍳\",\"color\":\"yellow\"}");
            if (temp) {
                run(s, "execute at " + anchor + " run kill @e[type=item_display,tag=astro_pl,distance=..0.3]");
                run(s, "kill " + anchor);
                run(s, "give " + name + " " + TABAK);
            } else {
                // the plate stays on the table, now empty and real
                run(s, "execute at " + anchor + " as @e[type=item_display,tag=astro_pl_vis,distance=..0.3] run tag @s add astro_pl_plate");
                run(s, "execute at " + anchor + " as @e[type=item_display,tag=astro_pl_vis,distance=..0.3] run tag @s remove astro_pl_vis");
                setName(s, anchor, "astro:tabak");
            }
            BUSY.remove(pid);
            BUSY.remove(anchorId);
        });
    }

    /** eat a plated meal that is in your hand: a plate appears in front of you for the cutscene */
    private static void eatFromHand(ServerPlayer p, String ut) {
        MinecraftServer s = p.level().getServer();
        int[] ns = nutritionOf(p.getMainHandItem());
        Vec3 look = p.getLookAngle();
        Vec3 flat = new Vec3(look.x, 0, look.z);
        if (flat.lengthSqr() < 1e-4) flat = new Vec3(0, 0, 1);
        flat = flat.normalize();
        Vec3 pos = p.position().add(flat.scale(0.9)).add(0, 0.85, 0);
        UUID anchor = UUID.randomUUID();
        run(s, in(p) + "run summon minecraft:marker " + xyz(pos) + " {UUID:" + uuidArr(anchor) + ",Tags:[\"astro_pl\"]}");
        UUID plate = summonDisplay(p, pos, "\"astro_pl_vis\"", 0.62f, 0.02);
        run(s, "item replace entity " + plate + " contents with " + TABAK);
        UUID food = summonDisplay(p, pos, "\"astro_pl_food\"", 0.42f, 0.07);
        moveOneFromHand(p, food.toString());
        cutscene(p, anchor.toString(), anchor, pos, ut, ns[0], ns[1], true);
    }

    // ------------------------------------------------------------------ plating in the air (old way, still works)
    private static void plateInHand(ServerPlayer p, ItemStack plate, ItemStack food) {
        ItemStack plated = food.copyWithCount(1);
        int[] ns = nutritionOf(food);
        CompoundTag t = tag(plated);
        t.putBoolean("astro_plated", true);
        t.putInt("pn", ns[0]);
        t.putFloat("ps", ns[1]);
        plated.set(DataComponents.CUSTOM_DATA, CustomData.of(t));
        plated.remove(DataComponents.FOOD);
        plated.remove(DataComponents.CONSUMABLE);
        plated.remove(DataComponents.USE_REMAINDER);
        Component old = plated.get(DataComponents.CUSTOM_NAME);
        String foodName = old != null ? old.getString() : "Yemek";
        plated.set(DataComponents.CUSTOM_NAME, Component.literal("🍽 " + foodName + " (Tabakta)")
                .withStyle(st -> st.withColor(ChatFormatting.GOLD).withBold(true).withItalic(false)));
        food.shrink(1);
        plate.shrink(1);
        if (!p.getInventory().add(plated)) p.level().addFreshEntity(new ItemEntity(p.level(), p.getX(), p.getY(), p.getZ(), plated));
        run(p.level().getServer(), "execute at " + p.getStringUUID() + " run playsound minecraft:block.decorated_pot.insert master @a ~ ~ ~ 1 1.2");
    }

    // ------------------------------------------------------------------ events
    private static boolean ours(Entity e) {
        Component n = e.getCustomName();
        return n != null && n.getString().startsWith("astro:");
    }

    static void init() {
        // shift + right-click on the top of a block = place
        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            if (!(player instanceof ServerPlayer p)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND || !p.isShiftKeyDown()) return InteractionResult.PASS;
            if (!isAstro(p.getMainHandItem()) || hit.getDirection() != Direction.UP) return InteractionResult.PASS;
            if (BUSY.contains(p.getUUID())) return InteractionResult.SUCCESS;
            place(p, hit.getBlockPos());
            return InteractionResult.SUCCESS;
        });

        // right-click a placed thing
        UseEntityCallback.EVENT.register((player, world, hand, entity, hitResult) -> {
            if (!(player instanceof ServerPlayer p) || !ours(entity)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND) return InteractionResult.SUCCESS;
            if (BUSY.contains(p.getUUID()) || BUSY.contains(entity.getUUID())) return InteractionResult.SUCCESS;
            String kind = entity.getCustomName().getString();
            ItemStack main = p.getMainHandItem();
            if (main.isEmpty() && p.isShiftKeyDown()) { pickUp(p, entity); return InteractionResult.SUCCESS; }
            if (kind.equals("astro:tabak") && isFood(main)) { putOnPlate(p, entity); return InteractionResult.SUCCESS; }
            if (kind.startsWith("astro:plated")) {
                String ut = utensil(main);
                if (ut == null) ut = utensil(p.getOffhandItem());
                if (ut == null) {
                    p.sendSystemMessage(Component.literal("§c🍴 Yemek için elinde Kaşık, Çatal veya Bıçak olmalı!"));
                    return InteractionResult.SUCCESS;
                }
                String[] a = kind.split(":");
                int n = a.length > 2 ? Integer.parseInt(a[2]) : 4, sat = a.length > 3 ? Integer.parseInt(a[3]) : 4;
                cutscene(p, entity.getStringUUID(), entity.getUUID(), entity.position(), ut, n, sat, false);
                return InteractionResult.SUCCESS;
            }
            if (kind.equals("astro:tabak")) p.sendSystemMessage(Component.literal("§6🍽 Tabağa yemek koymak için elinde bir Türk yemeği tutup sağ tıkla."));
            return InteractionResult.SUCCESS;
        });

        // left-click a placed thing = pick it up
        AttackEntityCallback.EVENT.register((player, world, hand, entity, hit) -> {
            if (!(player instanceof ServerPlayer p) || !ours(entity)) return InteractionResult.PASS;
            pickUp(p, entity);
            return InteractionResult.SUCCESS;
        });

        // in the air
        UseItemCallback.EVENT.register((player, world, hand) -> {
            if (!(player instanceof ServerPlayer p)) return InteractionResult.PASS;
            ItemStack main = p.getMainHandItem(), off = p.getOffhandItem();
            if (isTool(main, "tabak") && isFood(off)) {
                if (hand == InteractionHand.MAIN_HAND) plateInHand(p, main, off);
                return InteractionResult.SUCCESS;
            }
            if (isPlated(main)) {
                if (hand != InteractionHand.MAIN_HAND) return InteractionResult.SUCCESS;
                String ut = utensil(off);
                if (BUSY.contains(p.getUUID())) return InteractionResult.SUCCESS;
                if (ut != null) eatFromHand(p, ut);
                else p.sendSystemMessage(Component.literal("§c🍴 Sol eline Kaşık, Çatal veya Bıçak al! (ya da Shift + sağ tık ile masaya koy)"));
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });
    }
}
