package astro.mod;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Astro Mega Pickaxe: a netherite pickaxe tagged with custom_data {astro_mega:1b,size:N}.
 * Mines an N x N area and can break + collect bedrock. Works with vanilla clients.
 */
public final class MegaPick {
    private static final Map<UUID, Direction> FACE = new HashMap<>();
    private static boolean busy = false;

    private MegaPick() { }

    static boolean isMega(ItemStack s) {
        if (s == null || s.isEmpty()) return false;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd != null && cd.copyTag().contains("astro_mega");
    }

    static int size(ItemStack s) {
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        if (cd == null) return 3;
        int n = cd.copyTag().getIntOr("size", 3);
        return Math.max(1, Math.min(9, n));
    }

    private static Direction faceOf(ServerPlayer p) {
        Direction d = FACE.get(p.getUUID());
        if (d != null) return d;
        float pitch = p.getXRot();
        if (pitch > 45f || pitch < -45f) return Direction.UP;
        return p.getDirection();
    }

    private static void breakArea(ServerPlayer p, ServerLevel level, BlockPos center, Direction face, int size, boolean includeCenter) {
        if (busy) return;
        busy = true;
        try {
            int r = size / 2;
            Direction.Axis axis = face.getAxis();
            for (int a = -r; a <= r; a++) {
                for (int b = -r; b <= r; b++) {
                    if (!includeCenter && a == 0 && b == 0) continue;
                    BlockPos t = switch (axis) {
                        case X -> center.offset(0, a, b);
                        case Y -> center.offset(a, 0, b);
                        default -> center.offset(a, b, 0);
                    };
                    BlockState s = level.getBlockState(t);
                    if (s.isAir()) continue;
                    if (s.is(Blocks.BEDROCK)) {
                        if (t.getY() <= level.getMinY()) continue; // never open a hole into the void
                        level.removeBlock(t, false);
                        if (!p.isCreative()) Block.popResource(level, t, new ItemStack(Items.BEDROCK));
                        continue;
                    }
                    if (s.getDestroySpeed(level, t) < 0) continue; // barriers, portal frames, etc.
                    p.gameMode.destroyBlock(t);
                    if (!isMega(p.getMainHandItem())) return; // pickaxe broke
                }
            }
        } finally {
            busy = false;
        }
    }

    private static Component name(int n) {
        return Component.literal("Astro Mega Pickaxe [" + n + "x" + n + "]")
                .withStyle(st -> st.withColor(ChatFormatting.LIGHT_PURPLE).withBold(true).withItalic(false));
    }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static boolean ownerOrAdmin(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        if (p == null) return true;
        var team = src.getServer().getScoreboard().getPlayersTeam(p.getScoreboardName());
        return team != null && (team.getName().equals("astro_owner") || team.getName().equals("rank_admin"));
    }

    private static int setSize(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        ItemStack tool = p.getMainHandItem();
        if (!isMega(tool)) { src.sendFailure(Component.literal("Hold your Astro Mega Pickaxe in your main hand first.")); return 0; }
        int n = IntegerArgumentType.getInteger(c, "size");
        if (n % 2 == 0) { src.sendFailure(Component.literal("Use an odd number: 1, 3, 5, 7 or 9 (so it has a middle block).")); return 0; }
        CompoundTag tag = tool.get(DataComponents.CUSTOM_DATA).copyTag();
        tag.putInt("size", n);
        tool.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        tool.set(DataComponents.CUSTOM_NAME, name(n));
        src.sendSuccess(() -> Component.literal("§d✦ Mega Pickaxe now mines §e" + n + "x" + n + "§d!"), false);
        return 1;
    }

    private static int give(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        if (!ownerOrAdmin(src)) { src.sendFailure(Component.literal("Only the OWNER or ADMINS can spawn this. Craft it instead!")); return 0; }
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        run(src.getServer(), "give " + p.getName().getString() + " minecraft:netherite_pickaxe["
                + "custom_name={text:\"Astro Mega Pickaxe [3x3]\",color:\"light_purple\",bold:true,italic:false},"
                + "lore=[{text:\"Mines a 3x3 area and breaks bedrock!\",color:\"aqua\",italic:false},{text:\"Hold it and type /megasize 5 to change the size\",color:\"gray\",italic:false}],"
                + "enchantments={\"minecraft:efficiency\":6,\"minecraft:unbreaking\":10,\"minecraft:mending\":1,\"minecraft:fortune\":3},"
                + "custom_data={astro_mega:1b,size:3},rarity=\"epic\"]");
        return 1;
    }

    static void init() {
        // remember which face of the block the player hit, and let the mega pick break bedrock
        AttackBlockCallback.EVENT.register((player, world, hand, pos, direction) -> {
            if (!(player instanceof ServerPlayer sp) || !(world instanceof ServerLevel level)) return InteractionResult.PASS;
            FACE.put(sp.getUUID(), direction);
            if (hand != InteractionHand.MAIN_HAND || !isMega(sp.getMainHandItem())) return InteractionResult.PASS;
            if (level.getBlockState(pos).is(Blocks.BEDROCK) && !sp.isCreative()) {
                if (pos.getY() <= level.getMinY()) return InteractionResult.PASS;
                breakArea(sp, level, pos, direction, size(sp.getMainHandItem()), true);
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });

        // after a normal block is mined, mine the rest of the N x N area
        PlayerBlockBreakEvents.AFTER.register((world, player, pos, state, blockEntity) -> {
            if (busy) return;
            if (!(player instanceof ServerPlayer sp) || !(world instanceof ServerLevel level)) return;
            ItemStack tool = sp.getMainHandItem();
            if (!isMega(tool)) return;
            int n = size(tool);
            if (n <= 1) return;
            breakArea(sp, level, pos, faceOf(sp), n, false);
        });

        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) -> {
            d.register(Commands.literal("megasize")
                    .then(Commands.argument("size", IntegerArgumentType.integer(1, 9)).executes(MegaPick::setSize)));
            d.register(Commands.literal("megapick").executes(MegaPick::give));
        });
    }
}
