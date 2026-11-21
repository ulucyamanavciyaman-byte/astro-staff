package astro.mod;

import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.Nameable;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.item.alchemy.Potions;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Blocks;

import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Turkish coffee: a "Kahve Makinesi" (named brewing stand) + empty cup + coffee package + water
 * = a cup of Turkish coffee. Drinking it is detected by the astro_staff:coffee_drink advancement.
 */
public final class Coffee {
    private Coffee() { }

    private static final Set<BlockPos> BREWING = new HashSet<>();

    static final String CUP = "minecraft:flower_pot[custom_name={text:\"Boş Fincan\",color:\"white\",italic:false},"
            + "lore=[{text:\"Kahve makinesine sağ tıkla\",color:\"gray\",italic:false}],custom_data={astro_cup:1b}]";
    static final String PACKAGE = "minecraft:brown_dye[item_model=\"minecraft:brown_bundle\","
            + "custom_name={text:\"Türk Kahvesi Paketi\",color:\"gold\",bold:true,italic:false},"
            + "lore=[{text:\"Taze çekilmiş, 100g\",color:\"gray\",italic:false}],custom_data={astro_coffee_pkg:1b}]";
    static final String MAKER = "minecraft:brewing_stand[custom_name={text:\"Kahve Makinesi\",color:\"gold\",bold:true,italic:false},"
            + "lore=[{text:\"Elinde boş fincan + çantanda kahve paketi ve su ile sağ tıkla\",color:\"gray\",italic:false}]]";
    static final String COFFEE = "minecraft:flower_pot[custom_name={text:\"Türk Kahvesi\",color:\"gold\",bold:true,italic:false},"
            + "lore=[{text:\"Köpüklü, tam kıvamında ☕\",color:\"yellow\",italic:false}],"
            + "custom_data={astro_coffee:1b},max_stack_size=1,"
            + "consumable={consume_seconds:2.0f,animation:\"drink\",sound:\"minecraft:entity.generic.drink\",has_consume_particles:false,"
            + "on_consume_effects:[{type:\"minecraft:apply_effects\",effects:["
            + "{id:\"minecraft:speed\",duration:1200,amplifier:1},{id:\"minecraft:haste\",duration:1200,amplifier:1},{id:\"minecraft:night_vision\",duration:600,amplifier:0}]}]},"
            + "use_remainder={id:\"minecraft:flower_pot\",count:1,components:{\"minecraft:custom_name\":{text:\"Boş Fincan\",color:\"white\",italic:false},\"minecraft:custom_data\":{astro_cup:1b}}}]";

    private static boolean has(ItemStack s, String key) {
        if (s == null || s.isEmpty()) return false;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd != null && cd.copyTag().contains(key);
    }

    private static boolean isWaterBottle(ItemStack s) {
        if (!s.is(Items.POTION)) return false;
        PotionContents pc = s.get(DataComponents.POTION_CONTENTS);
        return pc != null && pc.is(Potions.WATER);
    }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static String dimId(ServerLevel level) {
        String s = String.valueOf(level.dimension());
        int i = s.lastIndexOf(" / ");
        if (i >= 0) s = s.substring(i + 3);
        return s.replace("]", "").trim();
    }

    private static void at(ServerLevel level, BlockPos p, String command) {
        run(level.getServer(), String.format(Locale.ROOT, "execute in %s positioned %d.5 %d.5 %d.5 run %s",
                dimId(level), p.getX(), p.getY(), p.getZ(), command));
    }

    private static void brew(ServerPlayer p, ServerLevel level, BlockPos pos) {
        String name = p.getName().getString();
        if (BREWING.contains(pos)) { p.sendSystemMessage(Component.literal("§6☕ Sabret, kahve pişiyor...")); return; }
        ItemStack cup = p.getMainHandItem();
        if (!has(cup, "astro_cup")) {
            p.sendSystemMessage(Component.literal("§6☕ Elinde §fBoş Fincan§6 tut, çantanda §eTürk Kahvesi Paketi§6 ve §bsu§6 (kova veya şişe) olsun, sonra sağ tıkla!"));
            return;
        }
        Inventory inv = p.getInventory();
        int pkg = -1, water = -1;
        for (int i = 0; i < inv.getContainerSize(); i++) {
            ItemStack s = inv.getItem(i);
            if (pkg < 0 && has(s, "astro_coffee_pkg")) pkg = i;
            if (water < 0 && (s.is(Items.WATER_BUCKET) || isWaterBottle(s))) water = i;
        }
        if (pkg < 0) { p.sendSystemMessage(Component.literal("§c☕ Türk Kahvesi Paketi lazım!")); return; }
        if (water < 0) { p.sendSystemMessage(Component.literal("§c☕ Su lazım! (su kovası veya su şişesi)")); return; }

        inv.getItem(pkg).shrink(1);
        ItemStack w = inv.getItem(water);
        if (w.is(Items.WATER_BUCKET)) inv.setItem(water, new ItemStack(Items.BUCKET));
        else { w.shrink(1); run(level.getServer(), "give " + name + " minecraft:glass_bottle"); }
        cup.shrink(1);

        BREWING.add(pos);
        p.sendSystemMessage(Component.literal("§6☕ Kahve pişiyor, köpüğü kaçmasın..."));
        at(level, pos, "playsound minecraft:block.brewing_stand.brew master @a ~ ~ ~ 1 0.8");
        for (int i = 0; i < 6; i++) {
            OnePunch.later(i * 10, () -> {
                at(level, pos, "particle minecraft:campfire_cosy_smoke ~ ~0.6 ~ 0.1 0.1 0.1 0.01 3 force");
                at(level, pos, "playsound minecraft:block.bubble_column.bubble_column_upwards_ambient master @a ~ ~ ~ 0.6 1.2");
            });
        }
        OnePunch.later(60, () -> {
            BREWING.remove(pos);
            run(level.getServer(), "give " + name + " " + COFFEE);
            at(level, pos, "playsound minecraft:entity.experience_orb.pickup master @a ~ ~ ~ 1 0.7");
            at(level, pos, "particle minecraft:happy_villager ~ ~0.8 ~ 0.3 0.3 0.3 0 10 force");
            run(level.getServer(), "tellraw " + name + " {\"text\":\"☕ Türk kahven hazır! Afiyet olsun.\",\"color\":\"gold\"}");
        });
    }

    private static int give(CommandContext<CommandSourceStack> c) {
        CommandSourceStack src = c.getSource();
        ServerPlayer p = src.getPlayer();
        if (p == null) { src.sendFailure(Component.literal("Players only.")); return 0; }
        var team = src.getServer().getScoreboard().getPlayersTeam(p.getScoreboardName());
        if (team == null || !(team.getName().equals("astro_owner") || team.getName().equals("rank_admin"))) {
            src.sendFailure(Component.literal("Sadece OWNER ve ADMIN. Herkes üretebilir: Kahve Makinesi, Fincan ve Paket tariflerine bak!"));
            return 0;
        }
        String n = p.getName().getString();
        run(src.getServer(), "give " + n + " " + MAKER);
        run(src.getServer(), "give " + n + " " + CUP + " 3");
        run(src.getServer(), "give " + n + " " + PACKAGE + " 3");
        run(src.getServer(), "give " + n + " minecraft:water_bucket");
        src.sendSuccess(() -> Component.literal("§6☕ Türk kahvesi seti verildi!"), false);
        return 1;
    }

    static void init() {
        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            if (!(player instanceof ServerPlayer sp) || !(world instanceof ServerLevel level)) return InteractionResult.PASS;
            BlockPos pos = hit.getBlockPos();
            if (!level.getBlockState(pos).is(Blocks.BREWING_STAND)) return InteractionResult.PASS;
            if (!(level.getBlockEntity(pos) instanceof Nameable n) || !n.hasCustomName()
                    || !n.getCustomName().getString().contains("Kahve Makinesi")) return InteractionResult.PASS;
            if (hand == InteractionHand.MAIN_HAND) brew(sp, level, pos);
            return InteractionResult.SUCCESS;
        });
        CommandRegistrationCallback.EVENT.register((d, registryAccess, environment) ->
                d.register(Commands.literal("kahve").executes(Coffee::give)));
    }
}
