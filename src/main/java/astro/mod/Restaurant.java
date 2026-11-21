package astro.mod;

import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * /turkmutfagi  - builds the Türk Mutfağı restaurant right in front of you (entrance facing you)
 * /turkmutfagiclear - removes it again (blocks, chefs, displays)
 */
public final class Restaurant {
    private Restaurant() { }

    private static final Path FILE = Paths.get("config", "astro_restaurant.txt");

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static boolean allowed(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        if (p == null) return true;
        var team = src.getServer().getScoreboard().getPlayersTeam(p.getScoreboardName());
        return team != null && (team.getName().equals("astro_owner") || team.getName().equals("rank_admin"));
    }

    private static String dimId(ServerPlayer p) {
        String s = String.valueOf(p.level().dimension());
        int i = s.lastIndexOf(" / ");
        if (i >= 0) s = s.substring(i + 3);
        return s.replace("]", "").trim();
    }

    private static int build(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!allowed(src)) { src.sendFailure(Component.literal("Sadece OWNER ve ADMIN restoran kurabilir.")); return 0; }
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        if (Files.exists(FILE)) {
            src.sendFailure(Component.literal("Zaten bir Türk Mutfağı var! Önce /turkmutfagiclear yaz."));
            return 0;
        }
        var dir = p.getDirection();               // the way the player is looking
        String d = dir.getName();                 // north / south / east / west
        int fx = dir.getStepX(), fz = dir.getStepZ();
        int x = (int) Math.floor(p.getX()) + fx * 7;
        int y = (int) Math.floor(p.getY()) - 1;   // floor replaces the ground layer
        int z = (int) Math.floor(p.getZ()) + fz * 7;
        String dim = dimId(p);
        try {
            Files.createDirectories(FILE.getParent());
            Files.writeString(FILE, dim + " " + x + " " + y + " " + z + " " + d);
        } catch (Exception ignored) { }
        run(src.getServer(), "execute in " + dim + " positioned " + x + " " + y + " " + z + " run function astro_staff:turk/rest_build_" + d);
        src.sendSuccess(() -> Component.literal("§6★ §cTÜRK MUTFAĞI §6kuruldu! §eİçerideki ustalardan zümrütle yemek alınır. Silmek için /turkmutfagiclear"), false);
        return 1;
    }

    private static int clear(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!allowed(src)) { src.sendFailure(Component.literal("Sadece OWNER ve ADMIN restoranı silebilir.")); return 0; }
        try {
            if (!Files.exists(FILE)) { src.sendFailure(Component.literal("Silinecek bir Türk Mutfağı yok.")); return 0; }
            String[] a = Files.readString(FILE).trim().split("\\s+");
            run(src.getServer(), "execute in " + a[0] + " positioned " + a[1] + " " + a[2] + " " + a[3]
                    + " run function astro_staff:turk/rest_clear_" + a[4]);
            Files.deleteIfExists(FILE);
        } catch (Exception e) {
            src.sendFailure(Component.literal("Silinemedi: " + e.getMessage()));
            return 0;
        }
        src.sendSuccess(() -> Component.literal("§6Türk Mutfağı silindi."), false);
        return 1;
    }

    static void init() {
        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) -> {
            d.register(Commands.literal("turkmutfagi").executes(Restaurant::build));
            d.register(Commands.literal("turkmutfagı").executes(Restaurant::build));
            d.register(Commands.literal("turkmutfagiclear").executes(Restaurant::clear));
            d.register(Commands.literal("turkmutfagıclear").executes(Restaurant::clear));
        });
    }
}
