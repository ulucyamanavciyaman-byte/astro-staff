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
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
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
 * Astro Mutfak: real cooking with 3D cookware.
 *  - Ocak = smoker (3D stove model from the resource pack). Shift + right-click it with an EMPTY hand = turn the gas on / off.
 *  - Vessels (Tava, Tencere, Fırın Tepsisi, Cezve, Çaydanlık, Kesme Tahtası, Karıştırma Kabı): Shift + right-click on top of a block.
 *    Everything except Tahta and Kase needs a burning Ocak (or a lit furnace / campfire, magma).
 *  - Right-click the vessel holding an ingredient = put it in (max 6). Right-click with an EMPTY hand = cook (animated).
 *  - Done -> right-click to take it. Leave it on a burning Ocak too long and it BURNS (turn the Ocak off to keep it warm).
 *  - Shift + right-click (empty hand) or hit the vessel = pick it up (ingredients come back).
 * Vessel state lives in its interaction entity name: astro:v:<vessel>:<i|c|d|b>:<data>
 */
public final class Kitchen {
    private Kitchen() { }

    record Recipe(int id, String vessel, String keys, int sec, String name, String human, String give) { }

    private static final List<Recipe> ALL = new ArrayList<>();
    private static final Map<String, Recipe> BY_KEY = new HashMap<>();
    private static final Set<UUID> BUSY = new HashSet<>();
    private static final Map<UUID, Long> DONE_TOKEN = new HashMap<>();
    private static long tokens = 0;
    private static final Path FILE = Paths.get("config", "astro_kitchen.txt");
    private static final String FLAT = "left_rotation:[-0.7071f,0f,0f,0.7071f]";
    private static final Set<String> HEAT = Set.of("tava", "tencere", "tepsi", "cezve", "caydanlik");
    private static final String BURNT = "minecraft:charcoal[custom_name={text:\"Yanm\u0131\u015f Yemek\",color:\"dark_gray\",italic:false},"
            + "lore=[{text:\"Ocakta unuttun... \u00e7\u00f6pe at\u0131labilir\",color:\"gray\",italic:false}]]";

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
            case "tava" -> "Tava"; case "tencere" -> "Tencere"; case "tepsi" -> "F\u0131r\u0131n Tepsisi";
            case "cezve" -> "Cezve"; case "tahta" -> "Kesme Tahtas\u0131"; case "kase" -> "Kar\u0131\u015ft\u0131rma Kab\u0131";
            case "caydanlik" -> "\u00c7aydanl\u0131k"; default -> v;
        };
    }
    private static boolean needsHeat(String v) { return HEAT.contains(v); }
    /** height of the model bottom above the surface (heat vessels sit on the pan supports of the Ocak) */
    private static double lift(String v) { return needsHeat(v) ? 0.0625 : 0.006; }
    /** where ingredients lie inside the vessel */
    private static double ingY(String v) {
        return switch (v) { case "tava" -> 0.12; case "tencere" -> 0.40; case "tepsi" -> 0.10; case "tahta" -> 0.075; case "kase" -> 0.14; default -> 0.2; };
    }
    private static boolean hidden(String v) { return v.equals("cezve") || v.equals("caydanlik"); }
    /** where the finished food shows */
    private static double topY(String v) {
        return switch (v) { case "tava" -> 0.2; case "tencere" -> 0.56; case "tepsi" -> 0.16; case "tahta" -> 0.13; case "kase" -> 0.42;
            case "cezve" -> 0.42; case "caydanlik" -> 0.9; default -> 0.3; };
    }
    private static String hitH(String v) {
        return switch (v) { case "tencere" -> "0.5f"; case "caydanlik" -> "0.8f"; case "cezve" -> "0.35f"; case "kase" -> "0.4f"; default -> "0.3f"; };
    }
    private static String yawQ(double dx, double dz) {
        double th = Math.atan2(-dx, -dz);
        return "[0f," + f(Math.sin(th / 2)) + "f,0f," + f(Math.cos(th / 2)) + "f]";
    }
    private static boolean isOcak(BlockState b) { return b.is(Blocks.SMOKER); }
    private static boolean isHeat(BlockState b) {
        if (b.is(Blocks.SMOKER) || b.is(Blocks.FURNACE) || b.is(Blocks.BLAST_FURNACE) || b.is(Blocks.CAMPFIRE) || b.is(Blocks.SOUL_CAMPFIRE))
            return b.hasProperty(BlockStateProperties.LIT) && b.getValue(BlockStateProperties.LIT);
        return b.is(Blocks.MAGMA_BLOCK) || b.is(Blocks.LAVA_CAULDRON);
    }
    private static BlockState below(Entity e) {
        return e.level().getBlockState(BlockPos.containing(e.getX(), e.getY() - 0.1, e.getZ()));
    }
    private static String norm(String s) {
        return s.replace("\u0130", "i").replace("I", "\u0131").toLowerCase(Locale.ROOT)
                .replace("\u0131", "i").replace("\u011f", "g").replace("\u00fc", "u").replace("\u015f", "s").replace("\u00f6", "o").replace("\u00e7", "c");
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
    private static void bar(MinecraftServer s, Entity e, String json) {
        run(s, "execute at " + e.getStringUUID() + " run title @a[distance=..8] actionbar " + json);
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
    private static String paper(String cmd) {
        return "{id:\"minecraft:paper\",count:1,components:{\"minecraft:custom_model_data\":{strings:[\"" + cmd + "\"]}}}";
    }

    // ------------------------------------------------------------------ the Ocak knob
    private static void toggleOcak(ServerPlayer p, Level world, BlockPos bp, BlockState st) {
        boolean lit = st.getValue(BlockStateProperties.LIT);
        world.setBlock(bp, st.setValue(BlockStateProperties.LIT, !lit), 3);
        MinecraftServer s = p.level().getServer();
        String D = "execute in " + dim(p) + " run ";
        String c = (bp.getX() + 0.5) + " " + (bp.getY() + 1.05) + " " + (bp.getZ() + 0.5);
        run(s, D + "playsound minecraft:block.lever.click master @a " + c + " 1 " + (lit ? "0.7" : "1.2"));
        if (!lit) {
            run(s, D + "playsound minecraft:item.flintandsteel.use master @a " + c + " 1 1.4");
            run(s, D + "playsound minecraft:block.fire.ambient master @a " + c + " 0.6 1.6");
            run(s, D + "particle minecraft:soul_fire_flame " + c + " 0.2 0.01 0.2 0.01 14 force");
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"\ud83d\udd25 Ocak yand\u0131 (gaz a\u00e7\u0131k)\",\"color\":\"aqua\"}");
        } else {
            run(s, D + "particle minecraft:smoke " + c + " 0.15 0.05 0.15 0.01 6 force");
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"Ocak kapand\u0131\",\"color\":\"gray\"}");
        }
    }

    // ------------------------------------------------------------------ actions
    private static void placeVessel(ServerPlayer p, BlockPos on, double surfaceY, String v) {
        MinecraftServer s = p.level().getServer();
        Vec3 pos = new Vec3(on.getX() + 0.5, surfaceY, on.getZ() + 0.5);
        String D = "execute in " + dim(p) + " run ";
        UUID d = UUID.randomUUID(), hit = UUID.randomUUID();
        String q = yawQ(p.getX() - pos.x, p.getZ() - pos.z);
        run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(d) + ",Tags:[\"astro_v_vessel\"],item:{id:\"minecraft:stone\",count:1},"
                + "transformation:{left_rotation:" + q + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(0.5 + lift(v)) + "f,0f],scale:[1f,1f,1f]}}");
        moveOneFromHand(p, d.toString());
        run(s, D + "summon minecraft:interaction " + xyz(pos) + " {UUID:" + uuidArr(hit) + ",width:0.75f,height:" + hitH(v) + ",response:1b,CustomName:\"astro:v:" + v + ":i:\"}");
        run(s, D + "playsound minecraft:block.metal.place master @a " + xyz(pos) + " 1 1.2");
        BlockState below = p.level().getBlockState(on);
        if (needsHeat(v) && !isHeat(below)) {
            if (isOcak(below))
                p.sendSystemMessage(Component.literal("\u00a7e\u26a0 Ocak kapal\u0131! \u00a7fShift + bo\u015f elle Ocak'a sa\u011f t\u0131kla \u2192 gaz\u0131 a\u00e7."));
            else
                p.sendSystemMessage(Component.literal("\u00a7e\u26a0 " + vesselName(v) + " ate\u015fte de\u011fil! Ocak'\u0131n (smoker), f\u0131r\u0131n veya kamp ate\u015finin \u00fcst\u00fcne koy."));
        }
    }

    private static void addIngredient(ServerPlayer p, Entity e, String v, String data) {
        MinecraftServer s = p.level().getServer();
        List<String> keys = new ArrayList<>();
        if (!data.isEmpty()) keys.addAll(Arrays.asList(data.split(",")));
        if (keys.size() >= 6) { p.sendSystemMessage(Component.literal("\u00a7c" + vesselName(v) + " dolu! (en fazla 6 malzeme)")); return; }
        ItemStack main = p.getMainHandItem();
        String k = key(main);
        String id = String.valueOf(BuiltInRegistries.ITEM.getKey(main.getItem()));
        keys.add(k);
        int n = keys.size();
        double ang = n * 2.4;
        Vec3 pos = e.position();
        double rad = v.equals("tencere") || v.equals("kase") ? 0.12 : 0.16;
        double ox = Math.cos(ang) * rad, oz = Math.sin(ang) * rad;
        String sc = hidden(v) ? "0.001f,0.001f,0.001f" : "0.3f,0.3f,0.3f";
        UUID d = UUID.randomUUID();
        run(s, "execute in " + dim(p) + " run summon minecraft:item_display " + xyz(pos.add(ox, 0, oz)) + " {UUID:" + uuidArr(d) + ",Tags:[\"astro_v_ing\"],item:{id:\"minecraft:stone\",count:1},"
                + "transformation:{" + FLAT + ",right_rotation:[0f," + f(Math.sin(ang / 2)) + "f,0f," + f(Math.cos(ang / 2)) + "f],translation:[0f,"
                + f(ingY(v) + n * 0.012) + "f,0f],scale:[" + sc + "]}}");
        moveOneFromHand(p, d.toString());
        String pn = p.getName().getString();
        if (id.equals("minecraft:milk_bucket") || id.equals("minecraft:water_bucket")) run(s, "give " + pn + " minecraft:bucket");
        if (id.equals("minecraft:honey_bottle") || id.equals("minecraft:potion")) run(s, "give " + pn + " minecraft:glass_bottle");
        setState(s, e, v, "i", String.join(",", keys));
        String D = "execute in " + dim(p) + " run ";
        run(s, D + "playsound minecraft:" + (k.equals("su") || id.equals("minecraft:milk_bucket") ? "item.bucket.empty" : "block.decorated_pot.insert")
                + " master @a " + xyz(pos) + " 1 " + f(0.8 + n * 0.1));
        if (k.equals("su") || id.equals("minecraft:milk_bucket"))
            run(s, D + "particle minecraft:splash " + xyz(pos.add(0, ingY(v) + 0.1, 0)) + " 0.1 0.05 0.1 0.1 10 force");
        List<String> sorted = new ArrayList<>(keys);
        sorted.sort(null);
        Recipe r = BY_KEY.get(v + "|" + String.join(",", sorted));
        if (r != null)
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"\u2714 " + r.name().replace("\"", "") + " tarifi haz\u0131r! Bo\u015f elle sa\u011f t\u0131kla = " + (needsHeat(v) ? "P\u0130\u015e\u0130R" : "HAZIRLA") + "\",\"color\":\"green\"}");
        else
            run(s, "title " + p.getStringUUID() + " actionbar {\"text\":\"Malzeme eklendi (" + n + "/6)\",\"color\":\"yellow\"}");
    }

    private static void startCooking(ServerPlayer p, Entity e, String v, String data) {
        MinecraftServer s = p.level().getServer();
        if (data.isEmpty()) {
            p.sendSystemMessage(Component.literal("\u00a76\ud83c\udf73 \u00d6nce malzeme koy! Elinde malzemeyle sa\u011f t\u0131kla. Tarifler: \u00a7e/tarif <yemek>"));
            return;
        }
        List<String> keys = new ArrayList<>(Arrays.asList(data.split(",")));
        keys.sort(null);
        Recipe r = BY_KEY.get(v + "|" + String.join(",", keys));
        if (r == null) {
            p.sendSystemMessage(Component.literal("\u00a7c\u274c Bu malzemelerle " + vesselName(v) + "'da yap\u0131lacak bir tarif yok! \u00a77(/tarif ile ara, Shift+sa\u011f t\u0131k ile malzemeleri geri al)"));
            return;
        }
        if (needsHeat(v)) {
            BlockState b = below(e);
            if (!isHeat(b)) {
                p.sendSystemMessage(Component.literal(isOcak(b)
                        ? "\u00a7c\ud83d\udd25 Ocak kapal\u0131! \u00a7fShift + bo\u015f elle Ocak'a sa\u011f t\u0131kla, gaz\u0131 a\u00e7, sonra pi\u015fir."
                        : "\u00a7c\ud83d\udd25 Ate\u015f yok! " + vesselName(v) + "'y\u0131 yanan bir Ocak'\u0131n \u00fcst\u00fcne koy."));
                return;
            }
        }
        setState(s, e, v, "c", String.valueOf(r.id()));
        cook(s, "execute in " + dim(p) + " run ", e, v, r);
    }

    /** the cooking animation */
    private static void cook(MinecraftServer s, String D, Entity e, String v, Recipe r) {
        BUSY.add(e.getUUID());
        Vec3 pos = e.position();
        int total = Math.max(40, r.sec() * 20);
        double iy = ingY(v);
        boolean gas = needsHeat(v) && isOcak(below(e));
        UUID fx = UUID.randomUUID();
        switch (v) {
            case "tahta" -> run(s, D + "summon minecraft:item_display " + xyz(pos.add(0.08, 0.35, 0)) + " {UUID:" + uuidArr(fx) + ",Tags:[\"astro_v_fx\"],teleport_duration:3,"
                    + "item:{id:\"minecraft:stick\",count:1,components:{\"minecraft:custom_model_data\":{strings:[\"bicak\"]}}},"
                    + "transformation:{left_rotation:[0f,0f,0.7071f,0.7071f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[0.5f,0.5f,0.5f]}}");
            case "tencere" -> run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(fx) + ",Tags:[\"astro_v_fx\"],item:" + paper("v_kapak") + ","
                    + "transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,1.0f,0f],scale:[1f,1f,1f]}}");
            case "kase" -> run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(fx) + ",Tags:[\"astro_v_fx\"],item:" + paper("v_cirpici") + ","
                    + "transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0.42f,0f],scale:[0.55f,0.55f,0.55f]}}");
            default -> { }
        }
        if (v.equals("tencere")) run(s, D + "playsound minecraft:block.iron_trapdoor.close master @a " + xyz(pos) + " 0.6 1.6");
        String fxU = fx.toString();
        for (int t = 0; t < total; t += 5) {
            final int tick = t;
            OnePunch.later(t, () -> {
                if (!e.isAlive()) return;
                boolean up = (tick / 5) % 2 == 0;
                int pct = Math.min(100, tick * 100 / total);
                int bars = pct / 10;
                String bar = "\u25ae".repeat(bars) + "\u25af".repeat(10 - bars);
                String what = switch (v) {
                    case "tahta" -> "\ud83d\udd2a Do\u011fran\u0131yor "; case "kase" -> "\ud83e\udd63 \u00c7\u0131rp\u0131l\u0131yor ";
                    case "caydanlik" -> "\ud83e\uded6 Demleniyor "; case "cezve" -> "\u2615 Kahve pi\u015fiyor "; case "tepsi" -> "\ud83d\udd25 F\u0131r\u0131nda ";
                    case "tencere" -> "\ud83c\udf72 Kayn\u0131yor "; default -> "\ud83c\udf73 K\u0131zar\u0131yor ";
                };
                bar(s, e, "{\"text\":\"" + what + bar + " " + pct + "%  \u2022 " + r.name().replace("\"", "") + "\",\"color\":\"gold\"}");
                if (gas) run(s, D + "particle minecraft:soul_fire_flame " + xyz(pos.add(0, 0.03, 0)) + " 0.17 0.0 0.17 0.0 3 force");
                switch (v) {
                    case "tava" -> {
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f," + (up ? "0.3827f" : "-0.3827f") + ",0f,0.9239f],translation:[0f," + f(up ? iy + 0.16 : iy) + "f,0f],scale:[0.3f,0.3f,0.3f]}}");
                        run(s, D + "particle minecraft:smoke " + xyz(pos.add(0, 0.2, 0)) + " 0.15 0.02 0.15 0.01 3 force");
                        if (tick % 10 == 0) run(s, D + "particle minecraft:white_smoke " + xyz(pos.add(0, 0.25, 0)) + " 0.1 0.02 0.1 0.01 2 force");
                        if (tick % 10 == 0) run(s, D + "playsound minecraft:block.campfire.crackle master @a " + xyz(pos) + " 1 1.5");
                        if (tick % 15 == 0) run(s, D + "playsound minecraft:block.fire.extinguish master @a " + xyz(pos) + " 0.15 2");
                    }
                    case "tencere" -> {
                        run(s, "data merge entity " + fxU + " {start_interpolation:0,interpolation_duration:2,transformation:{left_rotation:"
                                + (up ? "[0.0436f,0f,0f,0.999f]" : "[0f,0f,-0.0436f,0.999f]") + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + (up ? "1.03f" : "1.0f") + ",0f],scale:[1f,1f,1f]}}");
                        run(s, D + "particle minecraft:cloud " + xyz(pos.add(0, 0.58, 0)) + " 0.2 0.02 0.2 0.01 2 force");
                        if (tick % 10 == 0) run(s, D + "playsound minecraft:block.chain.hit master @a " + xyz(pos) + " 0.25 2");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.bubble_column.upwards_ambient master @a " + xyz(pos) + " 1 1.2");
                    }
                    case "caydanlik" -> {
                        run(s, D + "particle minecraft:cloud " + xyz(pos.add(0, 0.85, 0)) + " 0.05 0.02 0.05 0.01 1 force");
                        if (tick % 10 == 0) run(s, D + "particle minecraft:bubble_pop " + xyz(pos.add(0, 0.45, 0)) + " 0.2 0.1 0.2 0.01 4 force");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.bubble_column.upwards_ambient master @a " + xyz(pos) + " 0.8 1.4");
                    }
                    case "cezve" -> {
                        run(s, D + "particle minecraft:bubble_pop " + xyz(pos.add(0, 0.33, 0)) + " 0.06 0.01 0.06 0.01 3 force");
                        if (pct > 70) run(s, D + "particle minecraft:dust{color:[0.45,0.28,0.15],scale:0.7} " + xyz(pos.add(0, 0.36, 0)) + " 0.06 0.02 0.06 0 4 force");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.bubble_column.whirlpool_ambient master @a " + xyz(pos) + " 0.5 1.8");
                    }
                    case "tepsi" -> {
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(iy) + "f,0f],scale:[" + (up ? "0.34f,0.34f,0.34f" : "0.3f,0.3f,0.3f") + "]}}");
                        run(s, D + "particle minecraft:small_flame " + xyz(pos.add(0, 0.05, 0)) + " 0.3 0.01 0.3 0 2 force");
                        run(s, D + "particle minecraft:campfire_cosy_smoke " + xyz(pos.add(0, 0.3, 0)) + " 0.1 0.05 0.1 0.005 1 force");
                        if (tick % 20 == 0) run(s, D + "playsound minecraft:block.furnace.fire_crackle master @a " + xyz(pos) + " 1 1");
                    }
                    case "kase" -> {
                        double a = tick * 0.9;
                        double qy = Math.sin(a / 2), qw = Math.cos(a / 2);
                        run(s, "data merge entity " + fxU + " {start_interpolation:0,interpolation_duration:5,transformation:{left_rotation:[0.12f," + f(qy) + "f,0f," + f(qw)
                                + "f],right_rotation:[0f,0f,0f,1f],translation:[" + f(Math.cos(a) * 0.08) + "f,0.42f," + f(Math.sin(a) * 0.08) + "f],scale:[0.55f,0.55f,0.55f]}}");
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f," + f(Math.sin(a)) + "f,0f," + f(Math.cos(a)) + "f],translation:[0f," + f(iy) + "f,0f],scale:[0.28f,0.28f,0.28f]}}");
                        if (tick % 10 == 0) run(s, D + "playsound minecraft:block.chain.step master @a " + xyz(pos) + " 0.5 1.8");
                        if (tick % 10 == 5) run(s, D + "particle minecraft:splash " + xyz(pos.add(0, 0.3, 0)) + " 0.1 0.03 0.1 0 3 force");
                    }
                    default -> {   // tahta: chop chop
                        run(s, D + "tp " + fxU + " " + xyz(pos.add(0.05, up ? 0.45 : 0.12, 0)));
                        if (!up) {
                            run(s, D + "playsound minecraft:block.wood.hit master @a " + xyz(pos) + " 1 1.6");
                            run(s, D + "particle minecraft:composter " + xyz(pos.add(0, 0.15, 0)) + " 0.12 0.02 0.12 0 4 force");
                        }
                        run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:5,transformation:{"
                                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(iy) + "f,0f],scale:[" + f(0.3 - 0.16 * tick / (double) total) + "f,0.3f,0.3f]}}");
                    }
                }
            });
        }
        OnePunch.later(Math.max(0, total - 8), () -> run(s, near(e, "astro_v_ing") + "run data merge entity @s {start_interpolation:0,interpolation_duration:7,transformation:{"
                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(iy) + "f,0f],scale:[0.01f,0.01f,0.01f]}}"));
        if (v.equals("tencere"))   // lift the lid off
            OnePunch.later(Math.max(0, total - 6), () -> {
                run(s, "data merge entity " + fxU + " {start_interpolation:0,interpolation_duration:6,transformation:{left_rotation:[0f,0f,0.2588f,0.9659f],right_rotation:[0f,0f,0f,1f],translation:[0.35f,1.35f,0f],scale:[1f,1f,1f]}}");
                run(s, D + "particle minecraft:cloud " + xyz(pos.add(0, 0.6, 0)) + " 0.2 0.1 0.2 0.03 20 force");
                run(s, D + "playsound minecraft:block.iron_trapdoor.open master @a " + xyz(pos) + " 0.6 1.6");
            });
        OnePunch.later(total, () -> { if (e.isAlive()) finish(s, D, e, v, r); else BUSY.remove(e.getUUID()); });
    }

    private static void finish(MinecraftServer s, String D, Entity e, String v, Recipe r) {
        String u = e.getStringUUID();
        Vec3 pos = e.position();
        run(s, "execute at " + u + " run kill @e[type=item_display,tag=astro_v_ing,distance=..0.45]");
        run(s, "execute at " + u + " run kill @e[type=item_display,tag=astro_v_fx,distance=..1.6]");
        UUID res = UUID.randomUUID();
        double ty = topY(v);
        run(s, D + "summon minecraft:item_display " + xyz(pos) + " {UUID:" + uuidArr(res) + ",Tags:[\"astro_v_res\"],item:{id:\"minecraft:stone\",count:1},"
                + "transformation:{" + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(ty) + "f,0f],scale:[0.01f,0.01f,0.01f]}}");
        String give = r.give();
        String item = give.matches(".* \\d+$") ? give.substring(0, give.lastIndexOf(' ')) : give;
        run(s, "item replace entity " + res + " contents with " + item);
        OnePunch.later(2, () -> run(s, "data merge entity " + res + " {start_interpolation:0,interpolation_duration:8,transformation:{"
                + FLAT + ",right_rotation:[0f,0f,0f,1f],translation:[0f," + f(ty + 0.02) + "f,0f],scale:[0.45f,0.45f,0.45f]}}"));
        setState(s, e, v, "d", String.valueOf(r.id()));
        run(s, D + "playsound minecraft:block.note_block.bell master @a " + xyz(pos) + " 1 1.2");
        run(s, D + "playsound minecraft:entity.player.levelup master @a " + xyz(pos) + " 0.5 1.8");
        run(s, D + "particle minecraft:happy_villager " + xyz(pos.add(0, ty + 0.1, 0)) + " 0.25 0.15 0.25 0 12 force");
        run(s, D + "particle minecraft:poof " + xyz(pos.add(0, ty, 0)) + " 0.15 0.05 0.15 0.01 8 force");
        bar(s, e, "{\"text\":\"\u2714 " + r.name().replace("\"", "") + " haz\u0131r! Almak i\u00e7in sa\u011f t\u0131kla" + (needsHeat(v) ? " (yanmadan!)" : "") + "\",\"color\":\"green\"}");
        BUSY.remove(e.getUUID());
        if (!needsHeat(v)) return;
        long tk = ++tokens;
        DONE_TOKEN.put(e.getUUID(), tk);
        OnePunch.later(400, () -> {   // 20 s: smells burnt
            if (!e.isAlive() || !Long.valueOf(tk).equals(DONE_TOKEN.get(e.getUUID())) || !isHeat(below(e))) return;
            run(s, D + "particle minecraft:large_smoke " + xyz(pos.add(0, ty + 0.1, 0)) + " 0.1 0.05 0.1 0.01 6 force");
            bar(s, e, "{\"text\":\"\u26a0 " + r.name().replace("\"", "") + " YANMAK \u00dcZERE! Hemen al ya da Oca\u011f\u0131 kapat!\",\"color\":\"red\"}");
            run(s, D + "playsound minecraft:block.note_block.bit master @a " + xyz(pos) + " 1 0.6");
        });
        OnePunch.later(600, () -> {   // 30 s: burnt
            if (!e.isAlive() || !Long.valueOf(tk).equals(DONE_TOKEN.get(e.getUUID())) || !isHeat(below(e))) return;
            DONE_TOKEN.remove(e.getUUID());
            run(s, "item replace entity " + res + " contents with " + BURNT);
            setState(s, e, v, "b", String.valueOf(r.id()));
            run(s, D + "particle minecraft:large_smoke " + xyz(pos.add(0, ty + 0.1, 0)) + " 0.15 0.15 0.15 0.02 30 force");
            run(s, D + "playsound minecraft:block.fire.extinguish master @a " + xyz(pos) + " 1 0.6");
            bar(s, e, "{\"text\":\"\ud83d\udca8 " + r.name().replace("\"", "") + " YANDI! Ocakta unuttun...\",\"color\":\"dark_red\"}");
        });
    }

    private static void takeResult(ServerPlayer p, Entity e, String v, String st, String data) {
        MinecraftServer s = p.level().getServer();
        DONE_TOKEN.remove(e.getUUID());
        if (st.equals("b")) run(s, "give " + p.getName().getString() + " " + BURNT);
        else {
            int id;
            try { id = Integer.parseInt(data); } catch (Exception ex) { id = -1; }
            if (id >= 0 && id < ALL.size()) run(s, "give " + p.getName().getString() + " " + ALL.get(id).give());
        }
        run(s, "execute at " + e.getStringUUID() + " run kill @e[type=item_display,tag=astro_v_res,distance=..0.45]");
        setState(s, e, v, "i", "");
        run(s, "execute at " + p.getStringUUID() + " run playsound minecraft:entity.item.pickup master @a ~ ~ ~ 1 0.9");
    }

    private static void pickUp(ServerPlayer p, Entity e, String[] st) {
        MinecraftServer s = p.level().getServer();
        if (BUSY.contains(e.getUUID())) { p.sendSystemMessage(Component.literal("\u00a7c\ud83d\udd25 Pi\u015ferken alamazs\u0131n!")); return; }
        if (st[1].equals("d") || st[1].equals("b")) takeResult(p, e, st[0], st[1], st[2]);
        dropAll(s, p, e, "astro_v_ing");
        dropAll(s, p, e, "astro_v_vessel");
        run(s, "execute at " + e.getStringUUID() + " run kill @e[type=item_display,tag=astro_v_fx,distance=..1.6]");
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
            src.sendSuccess(() -> Component.literal("\u00a76\u00a7l\ud83c\udf73 ASTRO MUTFAK \u00a7r\u00a77\u2014 " + ALL.size() + " tarif"), false);
            src.sendSuccess(() -> Component.literal("\u00a7e1) \u00a7fOcak'\u0131 yak: \u00a7bShift + bo\u015f elle Ocak'a sa\u011f t\u0131k \u00a77(gaz a\u00e7/kapa)"), false);
            src.sendSuccess(() -> Component.literal("\u00a7e2) \u00a7fTava/Tencere/Tepsi/Cezve/\u00c7aydanl\u0131k'\u0131 Ocak'\u0131n \u00fcst\u00fcne \u00a7bShift+sa\u011f t\u0131k\u00a7f ile koy. Tahta & Kar\u0131\u015ft\u0131rma Kab\u0131 tezgahta \u00e7al\u0131\u015f\u0131r."), false);
            src.sendSuccess(() -> Component.literal("\u00a7e3) \u00a7fElinde malzemeyle kaba sa\u011f t\u0131kla \u2192 i\u00e7ine girer (en fazla 6)"), false);
            src.sendSuccess(() -> Component.literal("\u00a7e4) \u00a7fBo\u015f elle sa\u011f t\u0131kla \u2192 \u00a7cP\u0130\u015e\u0130R! \u00a7f\u2192 bitince sa\u011f t\u0131kla al. \u00a7c30 sn b\u0131rak\u0131rsan YANAR!"), false);
            src.sendSuccess(() -> Component.literal("\u00a77\u00d6rnek: \u00a7bS\u00fct + Yo\u011furt Mayas\u0131 \u00a77(tencere) \u2192 Yo\u011furt \u2192 \u00a7bYo\u011furt + Su + Tuz \u00a77(kar\u0131\u015ft\u0131rma kab\u0131) \u2192 Ayran"), false);
            src.sendSuccess(() -> Component.literal("\u00a77Ara: \u00a7b/tarif ayran\u00a77, \u00a7b/tarif kebap\u00a77, \u00a7b/tarif yo\u011furt"), false);
            return 1;
        }
        String nq = norm(q);
        int shown = 0;
        for (Recipe r : ALL) {
            if (!norm(r.name()).contains(nq)) continue;
            String line = "\u00a76" + r.name() + " \u00a77= \u00a7f" + r.human() + " \u00a78[" + vesselName(r.vessel()) + ", " + r.sec() + " sn]";
            src.sendSuccess(() -> Component.literal(line), false);
            if (++shown >= 10) break;
        }
        if (shown == 0) src.sendFailure(Component.literal("Tarif bulunamad\u0131: " + q));
        return 1;
    }

    private static int build(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!staff(src)) { src.sendFailure(Component.literal("Sadece OWNER ve ADMIN mutfak kurabilir.")); return 0; }
        ServerPlayer p = src.getPlayer();
        if (p == null) return 0;
        if (Files.exists(FILE)) { src.sendFailure(Component.literal("Zaten bir mutfak var! \u00d6nce /mutfakclear yaz.")); return 0; }
        var dir = p.getDirection();
        String d = dir.getName();
        int x = (int) Math.floor(p.getX()) + dir.getStepX() * 5;
        int y = (int) Math.floor(p.getY()) - 1;
        int z = (int) Math.floor(p.getZ()) + dir.getStepZ() * 5;
        try { Files.createDirectories(FILE.getParent()); Files.writeString(FILE, dim(p) + " " + x + " " + y + " " + z + " " + d); } catch (Exception ignored) { }
        src.getServer().getCommands().performPrefixedCommand(src.getServer().createCommandSourceStack(),
                "execute in " + dim(p) + " positioned " + x + " " + y + " " + z + " run function astro_staff:turk/kitchen_build_" + d);
        src.sendSuccess(() -> Component.literal("\u00a76\ud83c\udf73 Astro Mutfak kuruldu! \u00a7fOca\u011f\u0131 yakmak: \u00a7bShift + bo\u015f elle sa\u011f t\u0131k\u00a7f. \u00a7e/tarif \u00a7fyaz. Silmek: /mutfakclear"), false);
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
        src.sendSuccess(() -> Component.literal("\u00a76Mutfak silindi."), false);
        return 1;
    }

    // ------------------------------------------------------------------ init
    static void init() {
        load();

        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            if (!(player instanceof ServerPlayer p)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND || !p.isShiftKeyDown()) return InteractionResult.PASS;
            if (p.getMainHandItem().isEmpty()) {   // the Ocak knob
                BlockState st = world.getBlockState(hit.getBlockPos());
                if (isOcak(st) && st.hasProperty(BlockStateProperties.LIT)) {
                    toggleOcak(p, world, hit.getBlockPos(), st);
                    return InteractionResult.SUCCESS;
                }
                return InteractionResult.PASS;
            }
            String v = vesselOf(p.getMainHandItem());
            if (v.isEmpty() || hit.getDirection() != Direction.UP) return InteractionResult.PASS;
            placeVessel(p, hit.getBlockPos(), hit.getLocation().y, v);
            return InteractionResult.SUCCESS;
        });

        UseEntityCallback.EVENT.register((player, world, hand, entity, hitResult) -> {
            if (!(player instanceof ServerPlayer p) || !isVessel(entity)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND) return InteractionResult.SUCCESS;
            String[] st = state(entity);
            ItemStack main = p.getMainHandItem();
            if (main.isEmpty() && p.isShiftKeyDown()) { pickUp(p, entity, st); return InteractionResult.SUCCESS; }
            if (BUSY.contains(entity.getUUID())) {
                p.sendSystemMessage(Component.literal("\u00a76\ud83d\udd25 Sabret, haz\u0131rlan\u0131yor..."));
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
                default -> takeResult(p, entity, st[0], st[1], st[2]);
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
