package astro.mod;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Astro Mutfak: real cooking.
 *  - Vessels (Tava, Tencere, Fırın Tepsisi, Cezve, Kesme Tahtası): Shift + right-click on top of a block to place.
 *    Tava/Tencere/Tepsi/Cezve must stand on a heat source (Ocak = smoker, furnace, blast furnace, campfire, magma).
 *  - Right-click the vessel holding an ingredient = put it in (max 6).
 *  - Right-click with an EMPTY hand = cook (if the ingredients match a recipe) -> animated cooking.
 *  - When it is done right-click to take the food. Shift + right-click (empty hand) or left-click = pick the vessel up.
 *  - /tarif <yemek> shows recipes, /mutfak builds a full kitchen, /mutfakclear removes it.
 * State of every vessel lives in its interaction entity name: astro:v:<vessel>:<i|c|d>:<data>
 */
public final class Kitchen {
    private Kitchen() { }

    record Recipe(int id, String vessel, String keys, int sec, String name, String human, String give) { }

    private static final List<Recipe> ALL = new ArrayList<>();
    private static final Map<String, Recipe> BY_KEY = new HashMap<>();
    private static final Set<UUID> BUSY = new HashSet<>();
    private static final Path FILE = Paths.get("config", "astro_kitchen.txt");
    private static final String FLAT = "left_rotation:[-0.7071f,0f,0f,0.7071f]";

    // ------------------------------------------------------------------ helpers
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
    private static CompoundTag tag(ItemStack s) {
        if (s == null || s.isEmpty()) return null;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd == null ? null : cd.copyTag();
    }
    private static String vesselOf(ItemStack s) {
        CompoundTag t = tag(s);
        return t == null ? "" : t.getStringOr("astro_vessel", "");
    }
    /** recipe key of an item stack */
    static String key(ItemStack s) {
        CompoundTag t = tag(s);
        if (t != null) {
            String a = t.getStringOr("astro_ing", "");
            if (!a.isEmpty()) return "ing:" + a;
            String fd = t.getStringOr("astro_food", "");
            if (!fd.isEmpty() && !t.contains("astro_plated")) return "food:" + fd;
            if (t.contains("astro_coffee_pkg")) return "ing:kahve";
        }
        String id = String.valueOf(BuiltInRegistries.ITEM.getKey(s.getItem()));
        if (id.equals("minecraft:water_bucket") || id.equals("minecraft:potion")) return "su";
        return id;
    }
    private static String vesselName(String v) {
        return switch (v) {
            case "tava" -> "Tava"; case "tencere" -> "Tencere"; case "tepsi" -> "Fırın Tepsisi";
            case "cezve" -> "Cezve"; case "tahta" -> "Kesme Tahtası"; default -> v;
        };
    }
    private static boolean needsHeat(String v) { return !v.equals("tahta"); }
    private static boolean isHeat(BlockState b) {
        return b.is(Blocks.SMOKER) || b.is(Blocks.FURNACE) || b.is(Blocks.BLAST_FURNACE) || b.is(Blocks.CAMPFIRE)
                || b.is(Blocks.SOUL_CAMPFIRE) || b.is(Blocks.MAGMA_BLOCK) || b.is(Blocks.LAVA_CAULDRON);
    }
    private static String norm(String s) {
        return s.replace("İ", "i").replace("I", "ı").toLowerCase(Locale.ROOT)
                .replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c");
    }

    private static void load() {
        try (InputStream in = Kitchen.class.getResourceAsStream("/astro_recipes.txt")) {
            if (in == null) return;
            BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            String line;
            while ((line = r.readLine()) != null) {
                String[] a = line.split("\\|", 6);
                if (a.length < 6) continue;
                Recipe rc = new Recipe(ALL.size(), a[0], a[1], Integer.parseInt(a[2]), a[3], a[4], a[5]);
                ALL.add(rc);
                BY_KEY.putIfAbsent(a[0] + "|" + a[1], rc);
            }
        } catch (Exception ignored) { }
    }

    // ------------------------------------------------------------------ vessel state
    private static boolean isVessel(Entity e) {
        Component n = e.getCustomName();
        return n != null && n.getString().startsWith("astro:v:");
    }
    private static String[] state(Entity e) {   // [vessel, st, data]
        String[] a = e.getCustomName().getString().split(":", 5);
        return new String[]{a.length > 2 ? a[2] : "tava", a.length > 3 ? a[3] : "i", a.length > 4 ? a[4] : ""};
    }
    private static void setState(MinecraftServer s, Entity e, String v, String st, String data) {
        run(s, "data merge entity " + e.getStringUUID() + " {CustomName:\"astro:v:" + v + ":" + st + ":" + data + "\"}");
    }
    private static String near(Entity e, String tag) {
        return "execute at " + e.getStringUUID() + " as @e[type=item_display,tag=" + tag + ",distance=..0.45] ";
    }
    private static void moveOneFromHand(ServerPlayer p, String target) {
        ItemStack main = p.getMainHandItem();
        ItemStack one = main.copyWithCount(1);
        ItemStack rest = main.copyWithCount(main.getCount() - 1);
        p.setItemInHand(InteractionHand.MAIN_HAND, one);
        run(p.level().getServer(), "item replace entity " + target + " contents from entity " + p.getStringUUID() + " weapon.mainhand");
        p.setItemInHand(InteractionHand.MAIN_HAND, rest);
    }
    private static void dropAll(MinecraftServer s, ServerPlayer p, Entity e, String tag) {
        String sel = "execute at " + e.getStringUUID() + " as @e[type=item_display,tag=" + tag + ",distance=..0.45] ";
        for (int i = 0; i < 7; i++) {
            run(s, "execute at " + e.getStringUUID() + " as @e[type=item_display,tag=" + tag + ",tag=!astro_dropped,distance=..0.45,limit=1] at @s run summon minecraft:item ~ ~0.2 ~ {Tags:[\"astro_tmp_drop\"],PickupDelay:0,Item:{id:\"minecraft:stone\",count:1}}");
            run(s, "execute at " + e.getStringUUID() + " as @e[type=item_display,tag=" + tag + ",tag=!astro_dropped,distance=..0.45,limit=1] run item replace entity @e[type=item,tag=astro_tmp_drop,limit=1] contents from entity @s contents");
            run(s, "execute at " + e.getStringUUID() + " as @e[type=item_display,tag=" + tag + ",tag=!astro_dropped,distance=..0.45,limit=1] run tag @s add astro_dropped");
            run(s, "tp @e[type=item,tag=astro_tmp_drop] " + p.getStringUUID());
            run(s, "tag @e[type=item,tag=astro_tmp_drop] remove astro_tmp_drop");
        }
        run(s, sel + "run kill @s");
    }

    // ------------------------------------------------------------------ actions
    private static void placeVessel(ServerPlayer p, BlockPos on, String v) {
        MinecraftServer s = p.level().getServer();
        Vec3 pos = new Vec3(on.getX() + 0.5, on.getY() + 1.0, on.getZ() + 0.5);
        String D = "execute in " + dim(p) + " run ";
        UUID d = UUID.randomUUID(), hit = UUID.randomUUID();
        run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(d) + ",Tags:[\"astro_v_vessel\"],item:{id:\"minecraft:stone\",count:1},billboard:\"fixed\","
                + "transformation:{" + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.02f,0f],scale:[0.75f,0.75f,0.75f]}}");
        moveOneFromHand(p, d.toString());
        run(s, D + "summon minecraft:interaction " + xyz(pos) + " {UUID:" + uuidArr(hit) + ",width:0.7f,height:0.3f,response:1b,CustomName:\"astro:v:" + v + ":i:\"}");
        run(s, D + "playsound minecraft:block.metal.place master @a " + xyz(pos) + " 1 1.2");
        BlockState below = p.level().getBlockState(on);
        if (needsHeat(v) && !isHeat(below))
            p.sendSystemMessage(Component.literal("§e⚠ " + vesselName(v) + " ateşte değil! Ocak (smoker), fırın veya kamp ateşinin üstüne koy."));
    }

    private static void addIngredient(ServerPlayer p, Entity e, String v, String data) {
        MinecraftServer s = p.level().getServer();
        List<String> keys = new ArrayList<>();
        if (!data.isEmpty()) keys.addAll(Arrays.asList(data.split(",")));
        if (keys.size() >= 6) { p.sendSystemMessage(Component.literal("§c" + vesselName(v) + " dolu! (en fazla 6 malzeme)")); return; }
        ItemStack main = p.getMainHandItem();
        String k = key(main);
        String id = String.valueOf(BuiltInRegistries.ITEM.getKey(main.getItem()));
        keys.add(k);
        int n = keys.size();
        double ang = n * 2.4;
        Vec3 pos = e.position();
        double ox = Math.cos(ang) * 0.16, oz = Math.sin(ang) * 0.16;
        UUID d = UUID.randomUUID();
        run(s, "execute in " + dim(p) + " run summon minecraft:item_display " + xyz(pos.add(ox, 0, oz)) + " {UUID:" + uuidArr(d) + ",Tags:[\"astro_v_ing\"],item:{id:\"minecraft:stone\",count:1},"
                + "billboard:\"fixed\",transformation:{" + FLAT + ",right_rotation:[0f," + f(Math.sin(ang / 2)) + "f,0f," + f(Math.cos(ang / 2)) + "f],translation:[0f,"
                + f(0.06 + n * 0.012) + "f,0f],scale:[0.32f,0.32f,0.32f]}}");
        moveOneFromHand(p, d.toString());
        String pn = p.getName().getString();
        if (id.equals("minecraft:milk_bucket") || id.equals("minecraft:water_bucket")) run(s, "give " + pn + " minecraft:bucket");
        if (id.equals("minecraft:honey_bottle") || id.equals("minecraft:potion")) run(s, "give " + pn + " minecraft:glass_bottle");
        String joined = String.join(",", keys);
        setState(s, e, v, "i", joined);
        run(s, "execute in " + dim(p) + " run playsound minecraft:block.decorated_pot.insert master @a " + xyz(pos) + " 1 " + f(0.8 + n * 0.1));
        List<String> sorted = new ArrayList<>(keys);
        sorted.sort(null);
        Recipe r = BY_KEY.get(v + "|" + String.join(",", sorted));
        if (r != null)
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"✔ " + r.name().replace("\"", "") + " tarifi hazır! Boş elle sağ tıkla = PİŞİR\",\"color\":\"green\"}");
        else
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"Malzeme eklendi (" + n + "/6)\",\"color\":\"yellow\"}");
    }

    private static void startCooking(ServerPlayer p, Entity e, String v, String data) {
        MinecraftServer s = p.level().getServer();
        if (data.isEmpty()) {
            p.sendSystemMessage(Component.literal("§6🍳 Önce malzeme koy! Elinde malzemeyle sağ tıkla. Tarifler: §e/tarif <yemek>"));
            return;
        }
        List<String> keys = new ArrayList<>(Arrays.asList(data.split(",")));
        keys.sort(null);
        Recipe r = BY_KEY.get(v + "|" + String.join(",", keys));
        if (r == null) {
            p.sendSystemMessage(Component.literal("§c❌ Bu malzemelerle " + vesselName(v) + "'da yapılacak bir tarif yok! §7(/tarif ile ara, Shift+sağ tık ile malzemeleri geri al)"));
            return;
        }
        if (needsHeat(v)) {
            BlockState below = p.level().getBlockState(BlockPos.containing(e.getX(), e.getY() - 0.5, e.getZ()));
            if (!isHeat(below)) {
                p.sendSystemMessage(Component.literal("§c🔥 Ateş yok! " + vesselName(v) + "'yı Ocak'ın (veya fırın / kamp ateşinin) üstüne koy."));
                return;
            }
        }
        setState(s, e, v, "c", String.valueOf(r.id()));
        cook(p.level().getServer(), (ServerLevel) p.level(), "execute in " + dim(p) + " run ", e, v, r);
    }

    /** the cooking animation */
    private static void cook(MinecraftServer s, ServerLevel level, String D, Entity e, String v, Recipe r) {
        UUID id = e.getUUID();
        BUSY.add(id);
        String u = e.getStringUUID();
        Vec3 pos = e.position();
        int total = r.sec() * 20;
        UUID fx = UUID.randomUUID();
        if (v.equals("tahta")) {   // a knife that chops
            run(s, D + "summon minecraft:item_display " + xyz(pos.add(0.1, 0.35, 0)) + " {UUID:" + uuidArr(fx) + ",Tags:[\"astro_v_fx\"],billboard:\"fixed\",teleport_duration:3,"
                    + "item:{id:\"minecraft:stick\",count:1,components:{\"minecraft:custom_model_data\":{strings:[\"bicak\"]}}},"
                    + "transformation:{left_rotation:[0f,0f,0.7071f,0.7071f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[0.5f,0.5f,0.5f]}}");
        } else if (v.equals("tencere") || v.equals("cezve")) {  // a lid / steam spoon
            run(s, D + "summon minecraft:item_display " + xyz(pos.add(-0.15, 0.3, 0)) + " {UUID:" + uuidArr(fx) + ",Tags:[\"astro_v_fx\"],billboard:\"fixed\",teleport_duration:6,"
                    + "item:{id:\"minecraft:stick\",count:1,components:{\"minecraft:custom_model_data\":{strings:[\"kasik\"]}}},"
                    + "transformation:{left_rotation:[0f,0f,0.3827f,0.9239f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[0.45f,0.45f,0.45f]}}");
        }
        String fxU = fx.toString();
        for (int t = 0; t < total; t += 5) {
            final int tick = t;
            OnePunch.later(t, () -> {
                boolean up = (tick / 5) % 2 == 0;
                int pct = Math.min(100, tick * 100 / total);
                int bars = pct / 10;
                String bar = "▮".repeat(bars) + "▯".repeat(10 - bars);
                run(s, "execute at " + u + " run title @a[distance=..8] actionbar {\"text\":\"" + (v.equals("tahta") ? "🔪 Doğranıyor " : "🔥 Pişiyor ")
                        + bar + " " + pct + "%  • " + r.name().replace("\"", "") + "\",\"color\":\"gold\"}");
                switch (v) {
                    case "tava" -> {
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f," + (up ? "0.3827f" : "-0.3827f") + ",0f,0.9239f],translation:[0f," + (up ? "0.22f" : "0.07f") + ",0f],scale:[0.32f,0.32f,0.32f]}}");
                        run(s, D + "particle minecraft:smoke " + xyz(pos.add(0, 0.15, 0)) + " 0.15 0.02 0.15 0.01 4 force");
                        run(s, D + "particle minecraft:flame " + xyz(pos.add(0, -0.05, 0)) + " 0.25 0.01 0.25 0 3 force");
                        if (tick % 10 == 0) run(s, D + "playsound minecraft:block.campfire.crackle master @a " + xyz(pos) + " 1 1.4");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:entity.generic.burn master @a " + xyz(pos) + " 0.35 1.8");
                    }
                    case "tencere", "cezve" -> {
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f," + (up ? "0.7071f" : "0f") + ",0f," + (up ? "0.7071f" : "1f") + "],translation:[0f," + (up ? "0.12f" : "0.08f") + ",0f],scale:[0.3f,0.3f,0.3f]}}");
                        run(s, D + "tp " + fxU + " " + xyz(pos.add(up ? 0.15 : -0.15, 0.3, up ? 0.1 : -0.1)));
                        run(s, D + "particle minecraft:bubble_pop " + xyz(pos.add(0, 0.2, 0)) + " 0.15 0.03 0.15 0.01 5 force");
                        run(s, D + "particle minecraft:cloud " + xyz(pos.add(0, 0.45, 0)) + " 0.1 0.05 0.1 0.01 1 force");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.bubble_column.upwards_ambient master @a " + xyz(pos) + " 1 1.2");
                    }
                    case "tepsi" -> {
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.06f,0f],scale:[" + (up ? "0.36f,0.36f,0.36f" : "0.3f,0.3f,0.3f") + "]}}");
                        run(s, D + "particle minecraft:flame " + xyz(pos.add(0, -0.05, 0)) + " 0.3 0.01 0.3 0 4 force");
                        run(s, D + "particle minecraft:campfire_cosy_smoke " + xyz(pos.add(0, 0.3, 0)) + " 0.1 0.05 0.1 0.005 1 force");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.furnace.fire_crackle master @a " + xyz(pos) + " 1 1");
                    }
                    default -> {   // tahta: chop chop
                        run(s, D + "tp " + fxU + " " + xyz(pos.add(0.05, up ? 0.45 : 0.12, 0)));
                        if (!up) {
                            run(s, D + "playsound minecraft:block.wood.hit master @a " + xyz(pos) + " 1 1.6");
                            run(s, D + "particle minecraft:composter " + xyz(pos.add(0, 0.15, 0)) + " 0.12 0.02 0.12 0 4 force");
                        }
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.06f,0f],scale:[" + f(0.32 - 0.18 * tick / (double) total) + "f,0.32f,0.32f]}}");
                    }
                }
            });
        }
        // shrink the ingredients just before it is done
        OnePunch.later(Math.max(0, total - 8), () -> run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:7,transformation:{"
                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.08f,0f],scale:[0.01f,0.01f,0.01f]}}"));
        OnePunch.later(total, () -> finish(s, D, e, v, r));
    }

    private static void finish(MinecraftServer s, String D, Entity e, String v, Recipe r) {
        String u = e.getStringUUID();
        Vec3 pos = e.position();
        run(s, "execute at " + u + " run kill @e[type=item_display,tag=astro_v_ing,distance=..0.45]");
        run(s, "execute at " + u + " run kill @e[type=item_display,tag=astro_v_fx,distance=..0.8]");
        UUID res = UUID.randomUUID();
        run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(res) + ",Tags:[\"astro_v_res\"],item:{id:\"minecraft:stone\",count:1},billboard:\"fixed\","
                + "transformation:{" + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.1f,0f],scale:[0.01f,0.01f,0.01f]}}");
        String give = r.give();
        String item = give.matches(".* \\d+$") ? give.substring(0, give.lastIndexOf(' ')) : give;
        run(s, "item replace entity " + res + " contents with " + item);
        OnePunch.later(2, () -> run(s, "data merge entity " + res + " {start_interpolation:0,interpolation_duration:8,transformation:{"
                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f,0.12f,0f],scale:[0.55f,0.55f,0.55f]}}"));
        setState(s, e, v, "d", String.valueOf(r.id()));
        run(s, D + "playsound minecraft:block.note_block.bell master @a " + xyz(pos) + " 1 1.2");
        run(s, D + "playsound minecraft:entity.player.levelup master @a " + xyz(pos) + " 0.5 1.8");
        run(s, D + "particle minecraft:happy_villager " + xyz(pos.add(0, 0.3, 0)) + " 0.25 0.15 0.25 0 12 force");
        run(s, D + "particle minecraft:poof " + xyz(pos.add(0, 0.2, 0)) + " 0.15 0.05 0.15 0.01 8 force");
        run(s, "execute at " + u + " run title @a[distance=..8] actionbar {\"text\":\"✔ " + r.name().replace("\"", "") + " hazır! Almak için sağ tıkla\",\"color\":\"green\"}");
        BUSY.remove(e.getUUID());
    }

    private static void takeResult(ServerPlayer p, Entity e, String v, String data) {
        MinecraftServer s = p.level().getServer();
        int id;
        try { id = Integer.parseInt(data); } catch (Exception ex) { id = -1; }
        if (id >= 0 && id < ALL.size()) run(s, "give " + p.getName().getString() + " " + ALL.get(id).give());
        run(s, "execute at " + e.getStringUUID() + " run kill @e[type=item_display,tag=astro_v_res,distance=..0.45]");
        setState(s, e, v, "i", "");
        run(s, "execute at " + p.getStringUUID() + " run playsound minecraft:entity.item.pickup master @a ~ ~ ~ 1 0.9");
    }

    private static void pickUp(ServerPlayer p, Entity e, String[] st) {
        MinecraftServer s = p.level().getServer();
        if (BUSY.contains(e.getUUID())) { p.sendSystemMessage(Component.literal("§c🔥 Pişerken alamazsın!")); return; }
        if (st[1].equals("d")) takeResult(p, e, st[0], st[2]);
        dropAll(s, p, e, "astro_v_ing");
        dropAll(s, p, e, "astro_v_vessel");
        run(s, "execute at " + e.getStringUUID() + " run kill @e[type=item_display,tag=astro_v_fx,distance=..0.8]");
        run(s, "kill " + e.getStringUUID());
    }

    // ------------------------------------------------------------------ commands
    private static boolean staff(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        if (p == null) return true;
        var team = src.getServer().getScoreboard().getPlayersTeam(p.getScoreboardName());
        return team != null && (team.getName().equals("astro_owner") || team.getName().equals("rank_admin"));
    }

    private static int tarif(CommandContext<CommandSourceStack> c, String q) {
        CommandSourceStack src = c.getSource();
        if (q == null || q.isBlank()) {
            src.sendSuccess(() -> Component.literal("§6§l🍳 ASTRO MUTFAK §r§7— " + ALL.size() + " tarif"), false);
            src.sendSuccess(() -> Component.literal("§e1) §fTava/Tencere/Tepsi/Cezve'yi §6Ocak§f'ın üstüne Shift+sağ tıkla koy (Tahta için ateş gerekmez)"), false);
            src.sendSuccess(() -> Component.literal("§e2) §fElinde malzemeyle kaba sağ tıkla → içine girer"), false);
            src.sendSuccess(() -> Component.literal("§e3) §fBoş elle sağ tıkla → §cPİŞİR! §f(animasyonlu)"), false);
            src.sendSuccess(() -> Component.literal("§e4) §fPişince sağ tıkla al. Ara: §b/tarif pankek §7, §b/tarif kebap"), false);
            return 1;
        }
        String nq = norm(q);
        int shown = 0;
        for (Recipe r : ALL) {
            if (!norm(r.name()).contains(nq)) continue;
            String line = "§6" + r.name() + " §7= §f" + r.human() + " §8[" + vesselName(r.vessel()) + ", " + r.sec() + " sn]";
            src.sendSuccess(() -> Component.literal(line), false);
            if (++shown >= 8) break;
        }
        if (shown == 0) src.sendFailure(Component.literal("Tarif bulunamadı: " + q));
        return 1;
    }

    private static int build(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!staff(src)) { src.sendFailure(Component.literal("Sadece OWNER ve ADMIN mutfak kurabilir.")); return 0; }
        ServerPlayer p = src.getPlayer();
        if (p == null) return 0;
        if (Files.exists(FILE)) { src.sendFailure(Component.literal("Zaten bir mutfak var! Önce /mutfakclear yaz.")); return 0; }
        var dir = p.getDirection();
        String d = dir.getName();
        int x = (int) Math.floor(p.getX()) + dir.getStepX() * 5;
        int y = (int) Math.floor(p.getY()) - 1;
        int z = (int) Math.floor(p.getZ()) + dir.getStepZ() * 5;
        try { Files.createDirectories(FILE.getParent()); Files.writeString(FILE, dim(p) + " " + x + " " + y + " " + z + " " + d); } catch (Exception ignored) { }
        src.getServer().getCommands().performPrefixedCommand(src.getServer().createCommandSourceStack(),
                "execute in " + dim(p) + " positioned " + x + " " + y + " " + z + " run function astro_staff:turk/kitchen_build_" + d);
        src.sendSuccess(() -> Component.literal("§6🍳 Astro Mutfak kuruldu! §e/tarif §fyaz ve pişirmeye başla. Silmek: /mutfakclear"), false);
        return 1;
    }

    private static int clear(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!staff(src)) { src.sendFailure(Component.literal("Sadece OWNER ve ADMIN.")); return 0; }
        try {
            if (!Files.exists(FILE)) { src.sendFailure(Component.literal("Silinecek mutfak yok.")); return 0; }
            String[] a = Files.readString(FILE).trim().split("\\s+");
            run(src.getServer(), "execute in " + a[0] + " positioned " + a[1] + " " + a[2] + " " + a[3] + " run function astro_staff:turk/kitchen_clear_" + a[4]);
            Files.deleteIfExists(FILE);
        } catch (Exception ex) { src.sendFailure(Component.literal("Hata: " + ex.getMessage())); return 0; }
        src.sendSuccess(() -> Component.literal("§6Mutfak silindi."), false);
        return 1;
    }

    // ------------------------------------------------------------------ init
    static void init() {
        load();

        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            if (!(player instanceof ServerPlayer p)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND || !p.isShiftKeyDown()) return InteractionResult.PASS;
            String v = vesselOf(p.getMainHandItem());
            if (v.isEmpty() || hit.getDirection() != Direction.UP) return InteractionResult.PASS;
            placeVessel(p, hit.getBlockPos(), v);
            return InteractionResult.SUCCESS;
        });

        UseEntityCallback.EVENT.register((player, world, hand, entity, hitResult) -> {
            if (!(player instanceof ServerPlayer p) || !isVessel(entity)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND) return InteractionResult.SUCCESS;
            String[] st = state(entity);
            ItemStack main = p.getMainHandItem();
            if (main.isEmpty() && p.isShiftKeyDown()) { pickUp(p, entity, st); return InteractionResult.SUCCESS; }
            if (BUSY.contains(entity.getUUID())) {
                p.sendSystemMessage(Component.literal("§6🔥 Sabret, pişiyor..."));
                return InteractionResult.SUCCESS;
            }
            switch (st[1]) {
                case "i" -> {
                    if (!main.isEmpty()) addIngredient(p, entity, st[0], st[2]);
                    else startCooking(p, entity, st[0], st[2]);
                }
                case "c" -> {   // server restarted mid-cooking: just finish it
                    try {
                        Recipe r = ALL.get(Integer.parseInt(st[2]));
                        finish(p.level().getServer(), "execute in " + dim(p) + " run ", entity, st[0], r);
                    } catch (Exception ex) { setState(p.level().getServer(), entity, st[0], "i", ""); }
                }
                default -> takeResult(p, entity, st[0], st[2]);
            }
            return InteractionResult.SUCCESS;
        });

        AttackEntityCallback.EVENT.register((player, world, hand, entity, hit) -> {
            if (!(player instanceof ServerPlayer p) || !isVessel(entity)) return InteractionResult.PASS;
            pickUp(p, entity, state(entity));
            return InteractionResult.SUCCESS;
        });

        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) -> {
            d.register(Commands.literal("tarif").executes(c -> tarif(c, null))
                    .then(Commands.argument("yemek", StringArgumentType.greedyString()).executes(c -> tarif(c, StringArgumentType.getString(c, "yemek")))));
            d.register(Commands.literal("mutfak").executes(Kitchen::build));
            d.register(Commands.literal("mutfakclear").executes(Kitchen::clear));
        });
    }
}
