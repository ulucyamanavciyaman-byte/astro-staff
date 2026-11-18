package astro.mod;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.util.regex.Pattern;

/**
 * Astro Staff Commands - moderator commands for Astro SMP.
 * Who counts as staff: players on the astro_owner, rank_admin or rank_mod teams.
 * The actual kick/ban/tp is run by the server itself, so mods do NOT need OP.
 */
public class AstroStaff implements ModInitializer {
    private static final String STAFF_TAG = "astro_staff";
    private static final java.util.Set<String> STAFF_TEAMS = java.util.Set.of("astro_owner", "rank_admin", "rank_mod");
    private static final Pattern NAME = Pattern.compile("[A-Za-z0-9_]{1,16}");

    private static final SuggestionProvider<CommandSourceStack> ONLINE =
            (ctx, builder) -> SharedSuggestionProvider.suggest(ctx.getSource().getServer().getPlayerNames(), builder);

    @Override
    public void onInitialize() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> register(dispatcher));
    }

    // ---------------------------------------------------------------- helpers
    /** staff = on the astro_owner / rank_admin / rank_mod team */
    private static boolean onStaffTeam(MinecraftServer server, ServerPlayer p) {
        var team = server.getScoreboard().getPlayersTeam(p.getScoreboardName());
        return team != null && STAFF_TEAMS.contains(team.getName());
    }

    private static boolean isStaff(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        return p == null || onStaffTeam(src.getServer(), p); // console is always allowed
    }

    private static boolean deny(CommandSourceStack src) {
        if (isStaff(src)) return false;
        src.sendFailure(Component.literal("Only Astro SMP staff (MOD / ADMIN / OWNER) can use this command."));
        return true;
    }

    private static String selfName(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        return p == null ? "Console" : p.getName().getString();
    }

    private static String clean(String s) {
        return s.replace("\\", "").replace("\"", "'").replace("\n", " ");
    }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static boolean validName(CommandSourceStack src, String name) {
        if (NAME.matcher(name).matches()) return true;
        src.sendFailure(Component.literal("That is not a valid Minecraft name: " + name));
        return false;
    }

    /** returns the online player or null (and tells the sender) */
    private static ServerPlayer online(CommandSourceStack src, String name) {
        ServerPlayer t = src.getServer().getPlayerList().getPlayerByName(name);
        if (t == null) src.sendFailure(Component.literal(name + " is not online."));
        return t;
    }

    private static boolean protectedTarget(CommandSourceStack src, ServerPlayer target) {
        if (target != null && onStaffTeam(src.getServer(), target) && src.getPlayer() != null) {
            src.sendFailure(Component.literal("You can't use that on another staff member."));
            return true;
        }
        return false;
    }

    private static void ok(CommandSourceStack src, String msg) {
        src.sendSuccess(() -> Component.literal(msg), false);
    }

    private static void broadcast(MinecraftServer server, String target, String action, String by, String color) {
        run(server, "tellraw @a [{\"text\":\"" + target + "\",\"color\":\"" + color + "\",\"bold\":true},"
                + "{\"text\":\" " + action + " \",\"color\":\"gold\"},{\"text\":\"" + by + "\",\"color\":\"dark_aqua\"}]");
    }

    // ---------------------------------------------------------------- commands
    private static int kick(CommandContext<CommandSourceStack> c, String reason) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        String name = StringArgumentType.getString(c, "player");
        if (!validName(src, name)) return 0;
        ServerPlayer t = online(src, name);
        if (t == null || protectedTarget(src, t)) return 0;
        String real = t.getName().getString();
        String why = clean(reason == null ? "Kicked by an Astro SMP moderator." : reason);
        broadcast(src.getServer(), real, "was kicked by", selfName(src), "red");
        run(src.getServer(), "kick " + real + " " + why);
        ok(src, "Kicked " + real + ".");
        return 1;
    }

    private static int ban(CommandContext<CommandSourceStack> c, String reason) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        String name = StringArgumentType.getString(c, "player");
        if (!validName(src, name)) return 0;
        ServerPlayer t = src.getServer().getPlayerList().getPlayerByName(name);
        if (protectedTarget(src, t)) return 0;
        String real = t != null ? t.getName().getString() : name;
        String why = clean(reason == null ? "Banned by an Astro SMP moderator. Appeal on our Discord." : reason);
        if (t != null) run(src.getServer(), "tag " + real + " add astro_banned");
        broadcast(src.getServer(), real, "was BANNED by", selfName(src), "dark_red");
        run(src.getServer(), "ban " + real + " " + why);
        ok(src, "Banned " + real + ".");
        return 1;
    }

    private static int unban(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        String name = StringArgumentType.getString(c, "player");
        if (!validName(src, name)) return 0;
        run(src.getServer(), "pardon " + name);
        run(src.getServer(), "function astro_magic:owner/unban {name:\"" + name + "\"}"); // also clears the datapack soft-ban
        ok(src, "Unbanned " + name + ". They can join again.");
        return 1;
    }

    /** runs one of the Astro datapack staff tools as the staff player */
    private static int tool(CommandContext<CommandSourceStack> c, String function, boolean needsTarget) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        ServerPlayer me = src.getPlayer();
        if (me == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        String self = me.getName().getString();
        if (!needsTarget) {
            run(src.getServer(), "execute as " + self + " at @s run function astro_magic:" + function);
            return 1;
        }
        String name = StringArgumentType.getString(c, "player");
        if (!validName(src, name)) return 0;
        ServerPlayer t = online(src, name);
        if (t == null || protectedTarget(src, t)) return 0;
        String real = t.getName().getString();
        run(src.getServer(), "execute as " + self + " at @s run function astro_magic:" + function + " {name:\"" + real + "\"}");
        return 1;
    }

    private static int tp(CommandContext<CommandSourceStack> c, boolean here) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        ServerPlayer me = src.getPlayer();
        if (me == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        String name = StringArgumentType.getString(c, "player");
        if (!validName(src, name)) return 0;
        ServerPlayer t = online(src, name);
        if (t == null) return 0;
        if (here && protectedTarget(src, t)) return 0;
        String self = me.getName().getString(), real = t.getName().getString();
        run(src.getServer(), here ? "tp " + real + " " + self : "tp " + self + " " + real);
        ok(src, here ? "Brought " + real + " to you." : "Teleported to " + real + ".");
        return 1;
    }

    private static int staffChat(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        String msg = clean(StringArgumentType.getString(c, "message"));
        run(src.getServer(), "tellraw @a[tag=" + STAFF_TAG + "] [{\"text\":\"[STAFF] \",\"color\":\"dark_aqua\",\"bold\":true},"
                + "{\"text\":\"" + selfName(src) + ": \",\"color\":\"aqua\"},{\"text\":\"" + msg + "\",\"color\":\"white\"}]");
        return 1;
    }

    private static int help(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (deny(src)) return 0;
        String[] lines = {
                "§3§l⚔ Astro Staff Commands",
                "§e/mkick <player> [reason] §7- kick a player",
                "§e/mban <player> [reason] §7- ban a player",
                "§e/munban <player> §7- unban a player",
                "§e/mtp <player> §7- teleport to a player",
                "§e/mtphere <player> §7- bring a player to you",
                "§e/mfreeze <player> §7/ §e/munfreeze <player> §7- freeze / unfreeze",
                "§e/mspec <player> §7- see through their eyes (§e/mstop§7 to return)",
                "§e/minv <player> §7- open a copy of their inventory",
                "§e/sc <message> §7- staff-only chat"
        };
        for (String l : lines) ok(src, l);
        return 1;
    }

    private static void register(CommandDispatcher<CommandSourceStack> d) {
        d.register(Commands.literal("mkick")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE)
                        .executes(c -> kick(c, null))
                        .then(Commands.argument("reason", StringArgumentType.greedyString())
                                .executes(c -> kick(c, StringArgumentType.getString(c, "reason"))))));
        d.register(Commands.literal("mban")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE)
                        .executes(c -> ban(c, null))
                        .then(Commands.argument("reason", StringArgumentType.greedyString())
                                .executes(c -> ban(c, StringArgumentType.getString(c, "reason"))))));
        d.register(Commands.literal("munban")
                .then(Commands.argument("player", StringArgumentType.word()).executes(AstroStaff::unban)));
        d.register(Commands.literal("mtp")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tp(c, false))));
        d.register(Commands.literal("mtphere")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tp(c, true))));
        d.register(Commands.literal("mfreeze")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tool(c, "staff/freeze", true))));
        d.register(Commands.literal("munfreeze")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tool(c, "staff/unfreeze", true))));
        d.register(Commands.literal("mspec")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tool(c, "staff/spectate", true))));
        d.register(Commands.literal("minv")
                .then(Commands.argument("player", StringArgumentType.word()).suggests(ONLINE).executes(c -> tool(c, "staff/invsee", true))));
        d.register(Commands.literal("mstop").executes(c -> tool(c, "staff/stop", false)));
        d.register(Commands.literal("sc")
                .then(Commands.argument("message", StringArgumentType.greedyString()).executes(AstroStaff::staffChat)));
        d.register(Commands.literal("mhelp").executes(AstroStaff::help));
    }
}
