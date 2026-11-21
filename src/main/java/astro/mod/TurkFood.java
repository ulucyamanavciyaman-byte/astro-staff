package astro.mod;

import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.common.ClientboundResourcePackPushPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.UUID;

/**
 * Astro Türk Mutfağı: 300+ Turkish foods. The textures come from a resource pack that the mod
 * sends to every player on join (no server.properties needed). /turkyemegi spawns 2 chests full of food.
 */
public final class TurkFood {
    private TurkFood() { }

    private static final UUID PACK_ID = UUID.nameUUIDFromBytes("astro_turk_food_pack".getBytes(StandardCharsets.UTF_8));
    private static String url = null;
    private static String hash = "";

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static int spawn(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        var team = src.getServer().getScoreboard().getPlayersTeam(p.getScoreboardName());
        if (team == null || !(team.getName().equals("astro_owner") || team.getName().equals("rank_admin"))) {
            src.sendFailure(Component.literal("Sadece OWNER ve ADMIN Türk yemeği sandığı çıkarabilir."));
            return 0;
        }
        run(src.getServer(), "execute as " + p.getName().getString() + " at @s run function astro_staff:turk/spawn");
        return 1;
    }

    private static int resend(CommandContext<CommandSourceStack> c) {
        ServerPlayer p = c.getSource().getPlayer();
        if (p == null || url == null) return 0;
        p.connection.send(packet());
        return 1;
    }

    private static ClientboundResourcePackPushPacket packet() {
        return new ClientboundResourcePackPushPacket(PACK_ID, url, hash, false,
                Optional.of(Component.literal("§6Astro SMP §e- Türk Mutfağı dokuları (300+ yemek). Kabul et ki yemekleri gör!")));
    }

    static void init() {
        try (InputStream in = TurkFood.class.getResourceAsStream("/astro_pack.txt")) {
            if (in != null) {
                String[] parts = new String(in.readAllBytes(), StandardCharsets.UTF_8).trim().split("\\s+");
                if (parts.length > 0 && parts[0].startsWith("https://")) url = parts[0];
                if (parts.length > 1) hash = parts[1];
            }
        } catch (Exception ignored) { }

        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            if (url != null) handler.send(packet());
        });

        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) -> {
            d.register(Commands.literal("turkyemegi").executes(TurkFood::spawn));
            d.register(Commands.literal("yemekdoku").executes(TurkFood::resend));
        });
    }
}
