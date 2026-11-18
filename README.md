# Astro Staff Commands (Fabric 26.3)

Moderator commands for Astro SMP. Staff = OWNER + players on the `rank_mod` / `rank_admin` teams
(the Astro datapack tags them `astro_staff`). Mods do NOT need OP.

| Command | What it does |
|---|---|
| /mkick <player> [reason] | kick |
| /mban <player> [reason] | ban |
| /munban <player> | unban |
| /mtp <player> | teleport to player |
| /mtphere <player> | bring player to you |
| /mfreeze <player> / /munfreeze <player> | freeze / unfreeze |
| /mspec <player> / /mstop | spectate through their eyes / go back |
| /minv <player> | open a copy of their inventory |
| /sc <message> | staff-only chat |
| /mhelp | list of commands |

Staff can't be kicked/banned/frozen by other staff. Needs the astro_magic datapack on the server.

## Build (no PC setup needed)
Push this folder to a GitHub repo -> Actions tab -> "Build Astro Staff mod" -> download the
`astro-staff-mod` artifact -> put `astro-staff-1.0.0.jar` into the server `mods` folder (with Fabric API).
