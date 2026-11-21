package astro.mod;

import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

/**
 * One Punch Gloves (owner only): punching anything starts a short cutscene, then a giant red
 * punch wave one-shots the target, launches it with huge knockback and smashes a hole through
 * a brand-new mountain. Server-side only, works for vanilla clients.
 */
public final class OnePunch {
    private OnePunch() { }

    // ------------------------------------------------------------------ tiny tick scheduler
    private static final class Task { int ticks; final Runnable r; Task(int t, Runnable r) { ticks = t; this.r = r; } }
    private static final List<Task> TASKS = new ArrayList<>();
    private static final Set<UUID> BUSY = new HashSet<>();

    static void later(int ticks, Runnable r) { TASKS.add(new Task(ticks, r)); }

    private static void tick(MinecraftServer server) {
        if (TASKS.isEmpty()) return;
        List<Task> due = new ArrayList<>();
        for (Task t : TASKS) if (--t.ticks <= 0) due.add(t);
        TASKS.removeAll(due);
        for (Task t : due) {
            try { t.r.run(); } catch (Exception ignored) { }
        }
    }

    // ------------------------------------------------------------------ helpers
    static boolean isGloves(ItemStack s) {
        if (s == null || s.isEmpty()) return false;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd != null && cd.copyTag().contains("astro_punch");
    }

    private static boolean isOwner(MinecraftServer server, ServerPlayer p) {
        var team = server.getScoreboard().getPlayersTeam(p.getScoreboardName());
        return team != null && team.getName().equals("astro_owner");
    }

    private static String dimId(ServerLevel level) {
        String s = String.valueOf(level.dimension());
        int i = s.lastIndexOf(" / ");
        if (i >= 0) s = s.substring(i + 3);
        return s.replace("]", "").trim();
    }

    private static String f(double d) { return String.format(Locale.ROOT, "%.2f", d); }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static void at(ServerLevel level, double x, double y, double z, String command) {
        run(level.getServer(), "execute in " + dimId(level) + " positioned " + f(x) + " " + f(y) + " " + f(z) + " run " + command);
    }

    // ------------------------------------------------------------------ the mountain + hole
    private static void buildMountain(ServerLevel level, int cx, int baseY, int cz) {
        int R = 30, H = 50;
        RandomSource rnd = level.getRandom();
        BlockState stone = Blocks.STONE.defaultBlockState(), andesite = Blocks.ANDESITE.defaultBlockState(),
                grass = Blocks.GRASS_BLOCK.defaultBlockState(), dirt = Blocks.DIRT.defaultBlockState(),
                snow = Blocks.SNOW_BLOCK.defaultBlockState(), gravel = Blocks.GRAVEL.defaultBlockState();
        for (int x = -R; x <= R; x++) {
            for (int z = -R; z <= R; z++) {
                double d = Math.sqrt(x * x + z * z) / R;
                if (d > 1) continue;
                double noise = Math.sin(x * 0.35) * Math.cos(z * 0.3) * 3 + Math.sin((x + z) * 0.15) * 2;
                int h = (int) (H * Math.pow(1 - d, 1.4) + noise * (1 - d));
                if (h < 1) continue;
                boolean snowy = h > H * 0.6;
                for (int y = 0; y <= h; y++) {
                    BlockPos p = new BlockPos(cx + x, baseY + y, cz + z);
                    if (level.isOutsideBuildHeight(p)) break;
                    if (level.getBlockEntity(p) != null || level.getBlockState(p).is(Blocks.BEDROCK)) continue;
                    BlockState s;
                    if (y == h) s = snowy ? snow : grass;
                    else if (!snowy && y >= h - 3) s = dirt;
                    else s = rnd.nextInt(6) == 0 ? andesite : (rnd.nextInt(25) == 0 ? gravel : stone);
                    level.setBlock(p, s, 2);
                }
            }
        }
    }

    private static void carveTunnel(ServerLevel level, Vec3 start, double dx, double dz, int len, int r, int floorY) {
        BlockState air = Blocks.AIR.defaultBlockState();
        double px = -dz, pz = dx; // sideways direction
        for (double t = 2; t <= len; t += 0.7) {
            for (double a = -r; a <= r; a += 0.7) {
                for (double b = -r; b <= r; b += 0.7) {
                    if (a * a + b * b > r * r) continue;
                    BlockPos p = BlockPos.containing(start.x + dx * t + px * a, start.y + b, start.z + dz * t + pz * a);
                    if (p.getY() < floorY || level.isOutsideBuildHeight(p)) continue;
                    BlockState s = level.getBlockState(p);
                    if (s.isAir() || s.is(Blocks.BEDROCK) || level.getBlockEntity(p) != null) continue;
                    level.setBlock(p, air, 2);
                }
            }
        }
    }

    // ------------------------------------------------------------------ the punch
    private static void punch(ServerPlayer owner, ServerLevel level, LivingEntity target) {
        UUID ownerId = owner.getUUID();
        BUSY.add(ownerId);
        String tid = target.getStringUUID();
        String oname = owner.getName().getString();
        Vec3 look = owner.getLookAngle();
        double len = Math.sqrt(look.x * look.x + look.z * look.z);
        double dx, dz;
        if (len < 0.1) { dx = owner.getDirection().getStepX(); dz = owner.getDirection().getStepZ(); }
        else { dx = look.x / len; dz = look.z / len; }
        final double fdx = dx, fdz = dz;
        Vec3 o = owner.position();

        // ---- 1) wind-up cutscene (1.5 seconds)
        run(level.getServer(), "effect give " + tid + " minecraft:slowness 3 255 true");
        run(level.getServer(), "effect give " + tid + " minecraft:weakness 3 255 true");
        run(level.getServer(), "effect give " + oname + " minecraft:slowness 2 255 true");
        at(level, o.x, o.y, o.z, "effect give @a[distance=..80,name=!" + oname + "] minecraft:darkness 3 0 true");
        at(level, o.x, o.y, o.z, "title @a[distance=..80] times 5 40 10");
        at(level, o.x, o.y, o.z, "title @a[distance=..80] subtitle {\"text\":\"...okay.\",\"color\":\"gray\",\"italic\":true}");
        at(level, o.x, o.y, o.z, "title @a[distance=..80] title {\"text\":\"ONE PUNCH\",\"color\":\"red\",\"bold\":true}");
        at(level, o.x, o.y, o.z, "playsound minecraft:entity.warden.sonic_charge master @a ~ ~ ~ 4 0.6");
        at(level, o.x, o.y, o.z, "playsound minecraft:block.beacon.power_select master @a ~ ~ ~ 4 0.5");
        for (int i = 0; i < 6; i++) {
            later(i * 5, () -> {
                Vec3 p = owner.position();
                at(level, p.x, p.y + 1, p.z, "particle minecraft:dust{color:[1.0,0.0,0.0],scale:3.0} ~ ~ ~ 1.2 1.2 1.2 0 60 force");
                at(level, p.x, p.y + 1, p.z, "particle minecraft:electric_spark ~ ~ ~ 1 1 1 0.5 40 force");
                at(level, p.x, p.y, p.z, "particle minecraft:cloud ~ ~0.2 ~ 2 0.1 2 0.05 20 force");
            });
        }

        // ---- 2) THE PUNCH
        later(30, () -> {
            Vec3 p = owner.position();
            double eye = p.y + 1.5;
            at(level, p.x, p.y, p.z, "playsound minecraft:entity.generic.explode master @a ~ ~ ~ 6 0.5");
            at(level, p.x, p.y, p.z, "playsound minecraft:entity.lightning_bolt.thunder master @a ~ ~ ~ 6 0.6");
            at(level, p.x, p.y, p.z, "playsound minecraft:entity.warden.sonic_boom master @a ~ ~ ~ 6 0.5");
            at(level, p.x, p.y, p.z, "title @a[distance=..120] actionbar {\"text\":\"✦ SERIOUS PUNCH ✦\",\"color\":\"dark_red\",\"bold\":true}");
            // red shockwave cone along the punch
            for (int i = 2; i <= 80; i += 3) {
                double spread = 1 + i * 0.12;
                double x = p.x + fdx * i, z = p.z + fdz * i, y = eye + 4;
                at(level, x, y, z, "particle minecraft:dust{color:[1.0,0.05,0.05],scale:4.0} ~ ~ ~ " + f(spread) + " " + f(spread) + " " + f(spread) + " 0 80 force");
                if (i % 6 == 2) at(level, x, y, z, "particle minecraft:explosion_emitter ~ ~ ~ " + f(spread / 2) + " " + f(spread / 2) + " " + f(spread / 2) + " 0 2 force");
                if (i % 9 == 2) at(level, x, y, z, "particle minecraft:sonic_boom ~ ~ ~ 0 0 0 0 1 force");
            }
            // mountain ahead, then the hole the punch blasts through it
            int dist = 45;
            int cx = (int) Math.floor(p.x + fdx * dist), cz = (int) Math.floor(p.z + fdz * dist);
            int feet = (int) Math.floor(p.y);
            buildMountain(level, cx, feet - 2, cz);
            carveTunnel(level, new Vec3(p.x, feet + 6.5, p.z), fdx, fdz, dist + 36, 7, feet);
            // launch the target (~100 blocks of knockback)
            if (target.isAlive()) {
                target.setDeltaMovement(fdx * 8.0, 0.6, fdz * 8.0);
                if (target instanceof ServerPlayer tp) tp.connection.send(new ClientboundSetEntityMotionPacket(tp));
            }
            at(level, p.x, p.y, p.z, "effect clear @a[distance=..80] minecraft:darkness");
        });

        // ---- 3) one shot
        later(40, () -> {
            run(level.getServer(), "kill " + tid);
            BUSY.remove(ownerId);
        });
        later(200, () -> BUSY.remove(ownerId)); // safety unlock
    }

    // ------------------------------------------------------------------ command + events
    private static int give(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        if (!isOwner(src.getServer(), p)) { src.sendFailure(Component.literal("Only the OWNER can use the One Punch Gloves.")); return 0; }
        run(src.getServer(), "give " + p.getName().getString() + " minecraft:red_dye["
                + "custom_name={text:\"One Punch Gloves\",color:\"red\",bold:true,italic:false},"
                + "lore=[{text:\"Punch anything to end it in one hit.\",color:\"gold\",italic:false},{text:\"OWNER ONLY\",color:\"dark_red\",bold:true,italic:false}],"
                + "custom_data={astro_punch:1b},enchantment_glint_override=true,max_stack_size=1,rarity=\"epic\"]");
        src.sendSuccess(() -> Component.literal("§c✦ One Punch Gloves equipped. Hold them and punch something."), false);
        return 1;
    }

    static void init() {
        ServerTickEvents.END_SERVER_TICK.register(OnePunch::tick);

        AttackEntityCallback.EVENT.register((player, world, hand, entity, hit) -> {
            if (!(player instanceof ServerPlayer sp) || !(world instanceof ServerLevel level)) return InteractionResult.PASS;
            if (hand != InteractionHand.MAIN_HAND || !isGloves(sp.getMainHandItem())) return InteractionResult.PASS;
            if (!isOwner(level.getServer(), sp)) {
                sp.sendSystemMessage(Component.literal("§cThese gloves only obey the OWNER."));
                return InteractionResult.SUCCESS;
            }
            if (BUSY.contains(sp.getUUID())) return InteractionResult.SUCCESS;
            if (!(entity instanceof LivingEntity target) || !target.isAlive()) return InteractionResult.PASS;
            punch(sp, level, target);
            return InteractionResult.SUCCESS;
        });

        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) ->
                d.register(Commands.literal("onepunch").executes(OnePunch::give)));
    }
}
