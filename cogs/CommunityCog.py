import discord
from discord.ext import commands
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import json
import sqlite3
from cogs.utils import format_table
import re

class CommunityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="community")
    async def community(self, ctx, *args):
        """!community <username|@discorduser> [update]"""
        if not args:
            await ctx.send("Usage: !community <username|@discorduser> [update]")
            return

        username = args[0]
        force_update = False

        # Check if the first arg is a mention
        mention_match = re.match(r'^<@!?(\d+)>$', username)
        if mention_match:
            discord_id = mention_match.group(1)
            db = sqlite3.connect('dmzcord.db')
            c = db.cursor()
            c.execute("SELECT wzhub_username FROM user_sync WHERE discord_id = ?", (discord_id,))
            row = c.fetchone()
            db.close()
            if row:
                username = row[0]
            else:
                await ctx.send("That user has not synced their wzhub.gg username. They must run `!sync <wzhub_username>` first.")
                return

        if len(args) > 1 and args[1].lower() == "update":
            force_update = True

        db = sqlite3.connect('dmzcord.db')
        c = db.cursor()
        now = datetime.utcnow()
        force = force_update

        # Always send the initial message and keep the message object
        msg = await ctx.send(f"Fetching community loadouts for `{username}`... (this may take a few seconds)")

        # Check cache
        c.execute("SELECT data, last_updated FROM community_loadouts WHERE username = ?", (username.lower(),))
        row = c.fetchone()
        use_cache = False
        cache_timestamp = None
        if row and not force:
            data, last_updated = row
            last_dt = datetime.fromisoformat(last_updated)
            if now - last_dt < timedelta(hours=24):  # cache valid for 24h
                print(f"[COMMUNITY] Loaded {username} from cache. Cached at {last_dt}")
                loadouts = json.loads(data)
                # Sort alphabetically by gun_name
                loadouts = sorted(loadouts, key=lambda l: l["gun_name"].lower())
                use_cache = True
                cache_timestamp = last_updated
            else:
                print(f"[COMMUNITY] Cache for {username} expired or invalid.")
        else:
            if force:
                print(f"[COMMUNITY] Force update requested for {username}.")
            else:
                print(f"[COMMUNITY] No cache found for {username}.")

        if not use_cache:
            print(f"[COMMUNITY] Fetching from website and updating cache for {username}...")
            url = f"https://wzhub.gg/loadouts/community/{username}"
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                loadout_list_selector = '#__layout > div > div.wzh-community-user.wz-content > div.container > div > div.wzh-community-user__content > div > div.community-user-loadouts__list'
                try:
                    await page.wait_for_selector(loadout_list_selector, timeout=30000)
                    loadout_list = await page.query_selector(loadout_list_selector)
                    if not loadout_list:
                        await msg.edit(content=f"No loadouts found for `{username}`.")
                        await browser.close()
                        db.close()
                        return

                    loadout_cards = await loadout_list.query_selector_all('> .loadout-card')
                    if not loadout_cards:
                        await msg.edit(content=f"No loadouts found for `{username}`.")
                        await browser.close()
                        db.close()
                        return

                    loadouts = []
                    for card in loadout_cards:
                        gun_name_element = await card.query_selector('.gun-badge__text')
                        gun_name = (await gun_name_element.inner_text()).strip() if gun_name_element else "Unknown"
                        gun_type_element = await card.query_selector('.loadout-card__type')
                        gun_type = ""
                        if gun_type_element:
                            gun_type_text = await gun_type_element.inner_text()
                            gun_type = gun_type_text.split('\n')[0].strip()
                        gun_image_url = None
                        gun_image_element = await card.query_selector('.loadout-content__gun-image img')
                        if gun_image_element:
                            src = await gun_image_element.get_attribute('src')
                            if src:
                                gun_image_url = src if src.startswith("http") else f"https://wzhub.gg{src}"
                        attachments = []
                        attachment_cards = await card.query_selector_all('.attachment-card-content')
                        for att_card in attachment_cards:
                            name_div = await att_card.query_selector('.attachment-card-content__name > div')
                            att_name = (await name_div.inner_text()).strip() if name_div else "Unknown"
                            type_span = await att_card.query_selector('.attachment-card-content__name > span')
                            att_type = (await type_span.inner_text()).strip() if type_span else "Unknown"
                            tuning1 = tuning2 = "0.00"
                            counts = await att_card.query_selector_all('.attachment-card-content__counts > div')
                            if len(counts) >= 1:
                                t1_span = await counts[0].query_selector('span')
                                t1_val = (await t1_span.inner_text()).strip() if t1_span else "-"
                                tuning1 = t1_val if t1_val not in ["-", ""] else "0.00"
                            if len(counts) >= 2:
                                t2_span = await counts[1].query_selector('span')
                                t2_val = (await t2_span.inner_text()).strip() if t2_span else "-"
                                tuning2 = t2_val if t2_val not in ["-", ""] else "0.00"
                            attachments.append({
                                "name": att_name,
                                "type": att_type,
                                "tuning1": tuning1,
                                "tuning2": tuning2
                            })
                        loadouts.append({
                            "gun_name": gun_name,
                            "gun_type": gun_type,
                            "gun_image_url": gun_image_url,
                            "attachments": attachments
                        })

                    # MW2 gun list (case-insensitive match)
                    mw2_guns = [
                        "Chimera", "Lachmann-556", "STB 556", "M4", "M16", "Kastov 762", "Kastov-74u", "Kastov 545", "M13B", "TAQ-56",
                        "TAQ-V", "SO-14", "FTAC Recon", "Lachmann-762", "Lachmann Sub", "BAS-P", "MX9", "Vaznev-9K", "FSS Hurricane",
                        "Minibak", "PDSW 528", "VEL 46", "Fennec 45", "Lockwood 300", "Bryson 800", "Bryson 890", "Expedite 12",
                        "RAAL MG", "HCR 56", "556 Icarus", "RPK", "RAPP H", "Sakin MG38", "LM-S", "SP-R 208", "EBR-14", "SA-B 50",
                        "Lockwood MK2", "TAQ-M", "MCPR-300", "Victus XMR", "Signal 50", "LA-B 330", "SP-X 80", "X12", "X13 Auto",
                        ".50 GS", "P890", "Basilisk", "RPG-7", "Pila", "JOKR", "Strela-P", "Riot Shield", "Combat Knife"
                    ]
                    mw2_guns_lower = [g.lower() for g in mw2_guns]
                    loadouts = [
                        l for l in loadouts
                        if l["gun_name"].lower() in mw2_guns_lower
                    ]
                    if not loadouts:
                        await msg.edit(content=f"No MW2 loadouts found for `{username}`.")
                        await browser.close()
                        db.close()
                        return

                    # Sort alphabetically by gun_name before saving to cache
                    loadouts = sorted(loadouts, key=lambda l: l["gun_name"].lower())

                    # Save to cache
                    c.execute("REPLACE INTO community_loadouts (username, data, last_updated) VALUES (?, ?, ?)",
                              (username.lower(), json.dumps(loadouts), now.isoformat()))
                    db.commit()
                    cache_timestamp = now.isoformat()
                    print(f"[COMMUNITY] Cached {username} at {cache_timestamp}")
                    await browser.close()
                except Exception as e:
                    await msg.edit(content=f"Failed to load loadouts for `{username}`. Error: {e}")
                    await browser.close()
                    db.close()
                    return

        db.close()

        # Display logic (works for both cache and scrape)
        per_page = 5
        total_pages = (len(loadouts) + per_page - 1) // per_page

        async def send_page(page_num, msg_to_edit=None):
            start = page_num * per_page
            end = start + per_page
            page_loadouts = loadouts[start:end]
            view = discord.ui.View(timeout=120)
            for idx, loadout in enumerate(page_loadouts):
                view.add_item(discord.ui.Button(
                    label=loadout["gun_name"],
                    style=discord.ButtonStyle.primary,
                    custom_id=f"gun_{page_num}_{idx}"
                ))
            if total_pages > 1:
                if page_num > 0:
                    view.add_item(discord.ui.Button(label="Previous", style=discord.ButtonStyle.secondary, custom_id=f"prev_{page_num}"))
                if page_num < total_pages - 1:
                    view.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, custom_id=f"next_{page_num}"))
            if cache_timestamp:
                try:
                    dt = datetime.fromisoformat(cache_timestamp)
                    timestamp_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    timestamp_str = "unknown"
                header = f"**Community loadouts for `{username}` ({timestamp_str})**: (Page {page_num+1}/{total_pages})"
            else:
                header = f"**Community loadouts for `{username}`**: (Page {page_num+1}/{total_pages})"
            content = header
            if msg_to_edit:
                await msg_to_edit.edit(content=content, view=view, embed=None)
            else:
                return await ctx.send(content, view=view)

        async def send_gun_details(page_num, gun_idx, msg):
            loadout = loadouts[page_num * per_page + gun_idx]
            gun_name = loadout["gun_name"]
            gun_type = loadout["gun_type"]
            gun_image_url = loadout["gun_image_url"]
            attachments = loadout["attachments"]

            mw2_emoji = "<:mw2:1379964950008823889>"
            tuning_vert = "<:tuning_vert:1379959265422348389>"
            tuning_hor = "<:tuning_hor:1379959255628517458>"

            # Define attachment order
            attachment_order = [
                "optic", "muzzle", "barrel", "underbarrel", "rear grip",
                "stock", "laser", "ammunition", "magazine"
            ]
            # Sort attachments by the defined order
            attachments_sorted = sorted(
                attachments,
                key=lambda att: (
                    attachment_order.index(str(att.get("type", "")).strip().lower())
                    if att.get("type") and str(att.get("type", "")).strip().lower() in attachment_order
                    else 99
                )
            )

            lines = []
            lines.append(f"{mw2_emoji} {username}'s {gun_name} ({gun_type})")
            for att in attachments_sorted:
                att_type = att["type"].upper()
                att_name = att["name"]
                tuning1 = att["tuning1"]
                tuning2 = att["tuning2"]
                t1 = tuning1 if tuning1 not in ["-", "", None] else "0.00"
                t2 = tuning2 if tuning2 not in ["-", "", None] else "0.00"
                if t1 == "0.00" and t2 == "0.00":
                    lines.append(f"{att_type}: {att_name}")
                else:
                    tuning_str = f" {tuning_vert} {t1} {tuning_hor} {t2}"
                    lines.append(f"{att_type}: {att_name}{tuning_str}")

            # Add cache timestamp at the bottom
            if cache_timestamp:
                try:
                    dt = datetime.fromisoformat(cache_timestamp)
                    lines.append("")
                    lines.append(dt.strftime("Loadout cached: %A, %B %-d, %Y %-I:%M %p"))
                except Exception:
                    pass

            view = discord.ui.View(timeout=120)
            view.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id=f"back_{page_num}"))

            content = "\n".join(lines)
            if gun_image_url and gun_image_url.startswith("http"):
                embed = discord.Embed(color=discord.Color.blue())
                embed.set_image(url=gun_image_url)
                await msg.edit(content=content, embed=embed, view=view)
            else:
                await msg.edit(content=content, embed=None, view=view)

        await send_page(0, msg_to_edit=msg)

        if total_pages > 0:
            def check(interaction):
                return (
                    interaction.message.id == msg.id and
                    interaction.user.id == ctx.author.id
                )

            current_page = 0
            while True:
                try:
                    interaction = await ctx.bot.wait_for("interaction", timeout=120, check=check)
                    custom_id = interaction.data["custom_id"]
                    if custom_id.startswith("prev_"):
                        current_page -= 1
                        await send_page(current_page, msg)
                        await interaction.response.defer()
                    elif custom_id.startswith("next_"):
                        current_page += 1
                        await send_page(current_page, msg)
                        await interaction.response.defer()
                    elif custom_id.startswith("gun_"):
                        _, page_str, idx_str = custom_id.split("_")
                        await send_gun_details(int(page_str), int(idx_str), msg)
                        await interaction.response.defer()
                    elif custom_id.startswith("back_"):
                        page_num = int(custom_id.split("_")[1])
                        await send_page(page_num, msg)
                        await interaction.response.defer()
                except Exception:
                    break

        # Disable the view on timeout
        try:
            await msg.edit(view=None)
        except Exception:
            pass

    @commands.command(name="loadout")
    async def loadout(self, ctx, *, gun_name: str):
        """!loadout <gun_name|guns>"""
        db = sqlite3.connect('dmzcord.db')
        c = db.cursor()
        c.execute("SELECT data FROM community_loadouts")
        rows = c.fetchall()
        db.close()

        if gun_name.lower() == "guns":
            # Gather all guns by type
            guns = {}
            for (data,) in rows:
                try:
                    loadouts = json.loads(data)
                except Exception:
                    continue
                for loadout in loadouts:
                    gun_type = loadout["gun_type"]
                    gun_name_val = loadout["gun_name"]
                    if gun_type not in guns:
                        guns[gun_type] = set()
                    guns[gun_type].add(gun_name_val)
            if not guns:
                await ctx.send("No cached guns found.")
                return

            # Sort gun types and gun names
            gun_types = sorted(guns.keys(), key=lambda x: x.lower())
            guns_by_type = {gt: sorted(list(guns[gt]), key=lambda x: x.lower()) for gt in gun_types}

            # Helper to build the table for a gun type
            def build_table(gun_type):
                table_rows = [["Gun Name"]]
                for gun_name in guns_by_type[gun_type]:
                    table_rows.append([gun_name])
                return format_table(table_rows)

            # Initial state
            current_type_idx = 0
            current_type = gun_types[current_type_idx]
            content = f"**Available Guns for `{current_type}`:**\n{build_table(current_type)}"

            # Build the button view
            def get_view(selected_idx):
                view = discord.ui.View(timeout=120)
                for idx, gt in enumerate(gun_types):
                    style = discord.ButtonStyle.primary if idx == selected_idx else discord.ButtonStyle.secondary
                    view.add_item(discord.ui.Button(label=gt, style=style, custom_id=f"gun_type_{idx}"))
                return view

            msg = await ctx.send(content, view=get_view(current_type_idx))

            def check(interaction):
                return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

            while True:
                try:
                    interaction = await ctx.bot.wait_for("interaction", timeout=120, check=check)
                    custom_id = interaction.data["custom_id"]
                    if custom_id.startswith("gun_type_"):
                        idx = int(custom_id.split("_")[2])
                        current_type_idx = idx
                        current_type = gun_types[current_type_idx]
                        content = f"**Available Guns for `{current_type}`:**\n{build_table(current_type)}"
                        await msg.edit(content=content, view=get_view(current_type_idx))
                        await interaction.response.defer()
                except Exception:
                    break
            return

        db = sqlite3.connect('dmzcord.db')
        c = db.cursor()
        c.execute("SELECT username, data, last_updated FROM community_loadouts")
        rows = c.fetchall()
        db.close()

        found = []
        for username, data, last_updated in rows:
            try:
                loadouts = json.loads(data)
            except Exception:
                continue
            for loadout in loadouts:
                if gun_name.lower() in loadout["gun_name"].lower():
                    found.append((username, loadout, last_updated))
                    break  # Only need one match per username

        if not found:
            await ctx.send(f"No cached loadouts found for gun '{gun_name}'.")
            return

        # Sort by username
        found = sorted(found, key=lambda x: x[0].lower())

        # Prepare button view
        view = discord.ui.View(timeout=120)
        for idx, (username, _, _) in enumerate(found):
            view.add_item(discord.ui.Button(
                label=username,
                style=discord.ButtonStyle.primary,
                custom_id=f"loadout_{idx}"
            ))

        content = f"**Users with cached loadouts for '{gun_name}':**"
        msg = await ctx.send(content, view=view)

        async def show_user_loadout(idx):
            username, loadout, last_updated = found[idx]
            gun = loadout["gun_name"]
            gun_type = loadout["gun_type"]
            gun_image_url = loadout["gun_image_url"]
            attachments = loadout["attachments"]
            mw2_emoji = "<:mw2:1379964950008823889>"
            tuning_vert = "<:tuning_vert:1379959265422348389>"
            tuning_hor = "<:tuning_hor:1379959255628517458>"

            # Define attachment order
            attachment_order = [
                "optic", "muzzle", "barrel", "underbarrel", "rear grip",
                "stock", "laser", "ammunition", "magazine"
            ]
            # Sort attachments by the defined order
            attachments_sorted = sorted(
                attachments,
                key=lambda att: (
                    attachment_order.index(str(att.get("type", "")).strip().lower())
                    if att.get("type") and str(att.get("type", "")).strip().lower() in attachment_order
                    else 99
                )
            )

            lines = []
            lines.append(f"{mw2_emoji} {username}'s {gun} ({gun_type})")
            for att in attachments_sorted:
                att_type = att["type"].upper()
                att_name = att["name"]
                tuning1 = att["tuning1"]
                tuning2 = att["tuning2"]
                t1 = tuning1 if tuning1 not in ["-", "", None] else "0.00"
                t2 = tuning2 if tuning2 not in ["-", "", None] else "0.00"
                if t1 == "0.00" and t2 == "0.00":
                    lines.append(f"{att_type}: {att_name}")
                else:
                    tuning_str = f" {tuning_vert} {t1} {tuning_hor} {t2}"
                    lines.append(f"{att_type}: {att_name}{tuning_str}")

            # Add cache timestamp at the bottom
            try:
                dt = datetime.fromisoformat(last_updated)
                lines.append("")
                lines.append(dt.strftime("Loadout cached: %A, %B %-d, %Y %-I:%M %p"))
            except Exception:
                pass

            content = "\n".join(lines)
            view2 = discord.ui.View(timeout=120)
            view2.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="back"))
            if gun_image_url and gun_image_url.startswith("http"):
                embed = discord.Embed(color=discord.Color.blue())
                embed.set_image(url=gun_image_url)
                await msg.edit(content=content, embed=embed, view=view2)
            else:
                await msg.edit(content=content, embed=None, view=view2)

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        while True:
            try:
                interaction = await ctx.bot.wait_for("interaction", timeout=120, check=check)
                custom_id = interaction.data["custom_id"]
                if custom_id.startswith("loadout_"):
                    idx = int(custom_id.split("_")[1])
                    await show_user_loadout(idx)
                    await interaction.response.defer()
                elif custom_id == "back":
                    await msg.edit(content=content, embed=None, view=view)
                    await interaction.response.defer()
            except Exception:
                break

        # Disable the view on timeout
        try:
            await msg.edit(view=None)
        except Exception:
            pass

    @commands.command(name="sync")
    async def sync(self, ctx, wzhub_username: str):
        """
        !sync <wzhub_username>
        Links your Discord account to your wzhub.gg username.
        """
        db = sqlite3.connect('dmzcord.db')
        c = db.cursor()
        c.execute("INSERT OR REPLACE INTO user_sync (discord_id, wzhub_username) VALUES (?, ?)",
                  (str(ctx.author.id), wzhub_username))
        db.commit()
        db.close()
        await ctx.send(f"✅ Synced your Discord account to wzhub.gg username `{wzhub_username}`.")

async def setup(bot):
    await bot.add_cog(CommunityCog(bot))