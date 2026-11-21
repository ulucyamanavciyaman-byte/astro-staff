package astro.mod;

import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;

/**
 * Plates & cutlery for the Turkish food:
 *  - Tabak in main hand + food in off hand, right-click  -> "Tabakta <food>"
 *  - plated food in main hand + Kaşık/Çatal/Bıçak in off hand, right-click -> eat it (+2 bonus), plate comes back
 */
public final class Plate {
    private Plate() { }

    static final String TABAK = "minecraft:bowl[custom_name={text:\"Tabak\",color:\"white\",bold:true,italic:false},"
            + "lore=[{text:\"Ana elinde tut, yemek sol elinde: sağ tıkla = tabağa koy\",color:\"gray\",italic:false}],"
            + "custom_model_data={strings:[\"tabak\"]},custom_data={astro_tool:\"tabak\"}]";

    private static CompoundTag tag(ItemStack s) {
        if (s == null || s.isEmpty()) return null;
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd == null ? null : cd.copyTag();
    }

    private static boolean isTool(ItemStack s, String key) {
        CompoundTag t = tag(s);
        return t != null && t.getStringOr("astro_tool", "").equals(key);
    }

    private static boolean isUtensil(ItemStack s) {
        return isTool(s, "kasik") || isTool(s, "catal") || isTool(s, "bicak");
    }

    private static boolean isFood(ItemStack s) {
        CompoundTag t = tag(s);
        return t != null && t.contains("astro_food") && !t.contains("astro_plated");
    }

    private static boolean isPlated(ItemStack s) {
        CompoundTag t = tag(s);
        return t != null && t.contains("astro_plated");
    }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    private static void plate(ServerPlayer p, ItemStack plate, ItemStack food) {
        ItemStack plated = food.copyWithCount(1);
        FoodProperties fp = plated.get(DataComponents.FOOD);
        int n = fp != null ? fp.nutrition() : 4;
        float s = fp != null ? fp.saturation() : 4f;
        CompoundTag t = tag(plated);
        t.putBoolean("astro_plated", true);
        t.putInt("pn", n);
        t.putFloat("ps", s);
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
        String n2 = p.getName().getString();
        run(p.level().getServer(), "execute as " + n2 + " at @s run playsound minecraft:block.decorated_pot.place master @a ~ ~ ~ 1 1.2");
        p.sendSystemMessage(Component.literal("§6🍽 " + foodName + " tabağa kondu! §7Sol eline kaşık/çatal/bıçak al ve sağ tıkla."));
    }

    private static void eat(ServerPlayer p, ItemStack plated, ItemStack utensil) {
        CompoundTag t = tag(plated);
        int n = t.getIntOr("pn", 4) + 2;
        float s = t.getFloatOr("ps", 4f) + 2f;
        var fd = p.getFoodData();
        fd.setFoodLevel(Math.min(20, fd.getFoodLevel() + n));
        fd.setSaturation(Math.min((float) fd.getFoodLevel(), fd.getSaturationLevel() + s));
        Component old = plated.get(DataComponents.CUSTOM_NAME);
        String name = old != null ? old.getString().replace("🍽 ", "").replace(" (Tabakta)", "") : "Yemek";
        plated.shrink(1);
        String pn = p.getName().getString();
        run(p.level().getServer(), "give " + pn + " " + TABAK);
        run(p.level().getServer(), "execute as " + pn + " at @s run playsound minecraft:entity.generic.eat master @a ~ ~ ~ 1 1");
        run(p.level().getServer(), "execute as " + pn + " at @s run playsound minecraft:entity.player.burp master @a ~ ~ ~ 0.6 1.1");
        run(p.level().getServer(), "execute as " + pn + " at @s anchored eyes run particle minecraft:happy_villager ^ ^ ^0.6 0.2 0.2 0.2 0 6");
        String with = isTool(utensil, "kasik") ? "kaşıkla" : isTool(utensil, "catal") ? "çatalla" : "bıçakla";
        p.sendSystemMessage(Component.literal("§a😋 " + name + " " + with + " yendi! Afiyet olsun."));
    }

    static void init() {
        UseItemCallback.EVENT.register((player, world, hand) -> {
            if (!(player instanceof ServerPlayer p)) return InteractionResult.PASS;
            ItemStack main = p.getMainHandItem(), off = p.getOffhandItem();
            if (isTool(main, "tabak") && isFood(off)) {
                if (hand == InteractionHand.MAIN_HAND) plate(p, main, off);
                return InteractionResult.SUCCESS;
            }
            if (isPlated(main)) {
                if (hand != InteractionHand.MAIN_HAND) return InteractionResult.SUCCESS;
                if (isUtensil(off)) eat(p, main, off);
                else p.sendSystemMessage(Component.literal("§c🍴 Tabaktan yemek için sol eline Kaşık, Çatal veya Bıçak al!"));
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });
    }
}
