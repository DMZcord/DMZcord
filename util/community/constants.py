MW2Emoji = "<:mw2:1379964950008823889>"
TuningVertEmoji = "<:tuning_vert:1379959265422348389>"
TuningHorEmoji = "<:tuning_hor:1379959255628517458>"

# Attachment display order
AttachmentOrder = [
    "optic", "muzzle", "barrel", "underbarrel", "rear grip",
    "stock", "laser", "ammunition", "magazine", "trigger action",
    "comb", "loader", "arms", "bolt", "cable", "guard", "lever",
    "rail", "carry handle"
]

# MW2 Gun Lists
MW2Guns = [
    "Chimera", "Lachmann-556", "STB 556", "M4", "M16", "Kastov 762", "Kastov-74u", "Kastov 545", "M13B", "TAQ-56",
    "TAQ-V", "SO-14", "FTAC Recon", "Lachmann-762", "Lachmann Sub", "BAS-P", "MX9", "Vaznev-9K", "FSS Hurricane",
    "Minibak", "PDSW 528", "VEL 46", "Fennec 45", "Lockwood 300", "Bryson 800", "Bryson 890", "Expedite 12",
    "RAAL MG", "HCR 56", "556 Icarus", "RPK", "RAPP H", "Sakin MG38", "LM-S", "SP-R 208", "EBR-14", "SA-B 50",
    "Lockwood MK2", "TAQ-M", "MCPR-300", "Victus XMR", "Signal 50", "LA-B 330", "SP-X 80", "X12", "X13 Auto",
    ".50 GS", "P890", "Basilisk", "RPG-7", "Pila", "JOKR", "Strela-P", "Riot Shield", "Combat Knife"
]

# Gun type categories
GunTypes = [
    "Assault Rifles", "SMGs", "LMGs", "Marksman Rifles",
    "Sniper Rifles", "Shotguns", "Pistols", "Launchers"
]

MW2GunsLower = [g.lower() for g in MW2Guns]

GunsPerClass = {
    "AR": [
        "M4",
        "TAQ-56",
        "Kastov 762",
        "Kastov 545",
        "Kastov-74u",
        "M16",
        "STB 556",
        "Lachmann-556",
        "M13B",
        "Chimera",
        "Iso Hemlock",
        "Tempus Razorback",
        "FR Avancer",
        "M13C",
        "TR-76 Geist"
    ],
    "SMG": [
        "VEL 46",
        "MX9",
        "Lachmann Sub",
        "Vaznev-9K",
        "FSS Hurricane",
        "Minibak",
        "PDSW 528",
        "Fennec 45",
        "BAS-P",
        "Iso 45",
        "Lachmann Shroud",
        "Iso 9mm"
    ],
    "LMG": [
        "Sakin MG38",
        "HCR 56",
        "556 Icarus",
        "RAAL MG",
        "RPK",
        "RAPP H"
    ],
    "B.RIFLES": [
        "Lachmann-762",
        "SO-14",
        "TAQ-V",
        "FTAC Recon",
        "Cronen Squall"
    ],
    "SHOTGUN": [
        "Lockwood 300",
        "Bryson 800",
        "Bryson 890",
        "Expedite 12",
        "MX Guardian",
        "KV Broadside"
    ],
    "SNIPER": [
        "MCPR-300",
        "Signal 50",
        "LA-B 330",
        "SP-X 80",
        "Victus XMR",
        "FJX Imperium",
        "Carrack .300"
    ],
    "RIFLE": [
        "EBR-14",
        "SP-R 208",
        "Lockwood MK2",
        "LM-S",
        "SA-B 50",
        "TAQ-M",
        "Crossbow",
        "Tempus Torrent"
    ],
    "PISTOL": [
        "P890",
        "X12",
        ".50 GS",
        "Basilisk",
        "X13 Auto",
        "GS Magna",
        "FTAC Siege",
        "9mm Daemon"
    ]
}

Gun_Image_Urls = {
    ".50 GS": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/395.png?v=2",
    "556 ICARUS": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/367.png?v=2",
    "9MM DAEMON": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/9mm_daemon.png?v=2",
    "BAS-P": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/400.png?v=2",
    "BASILISK": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/397.png?v=2",
    "BRYSON 800": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/382.png?v=2",
    "BRYSON 890": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/383.png?v=2",
    "CARRACK .300": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/carrack_color.png?v=2",
    "CHIMERA": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/402.png?v=2",
    "CRONEN SQUALL": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/414.png?v=2",
    "CROSSBOW": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/409-1.png?v=2",
    "EBR-14": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/388.png?v=2",
    "EXPEDITE 12": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/381.png?v=2",
    "FENNEC 45": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/379.png?v=2",
    "FJX IMPERIUM": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/415.png?v=2",
    "FR AVANCER": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/fravancer_color.png?v=2",
    "FSS HURRICANE": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/372.png?v=2",
    "FTAC RECON": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/365.png?v=2",
    "FTAC SIEGE": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/416.png?v=2",
    "GS MAGNA": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/gs_magna.png",
    "HCR 56": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/366.png?v=2",
    "ISO 45": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/419.png?v=2",
    "ISO 9MM": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/iso9.png",
    "ISO HEMLOCK": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/410-1.png?v=2",
    "KASTOV 545": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/361.png?v=2",
    "KASTOV 762": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/355.png?v=2",
    "KASTOV-74U": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/360.png?v=2",
    "KV BROADSIDE": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/411-1.png?v=2",
    "LA-B 330": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/386.png?v=2",
    "LACHMANN SHROUD": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/lachmann_shroud.png?v=2",
    "LACHMANN SUB": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/376.png?v=2",
    "LACHMANN-556": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/356.png?v=2",
    "LACHMANN-762": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/362.png?v=2",
    "LM-S": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/390.png?v=2",
    "LOCKWOOD 300": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/380.png?v=2",
    "LOCKWOOD MK2": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/392.png?v=2",
    "M13B": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/399.png?v=2",
    "M13C": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/m13c.png?v=2",
    "M16": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/359.png?v=2",
    "M4": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/357.png?v=2",
    "MCPR-300": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/384.png?v=2",
    "MINIBAK": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/374.png?v=2",
    "MX GUARDIAN": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/421.png?v=2",
    "MX9": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/375.png?v=2",
    "P890": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/394.png?v=2",
    "PDSW 528": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/378.png?v=2",
    "RAAL MG": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/370.png?v=2",
    "RAPP H": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/369.png?v=2",
    "RPK": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/368.png?v=2",
    "SA-B 50": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/393.png?v=2",
    "SAKIN MG38": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/371.png?v=2",
    "SIGNAL 50": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/385.png?v=2",
    "SO-14": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/363.png?v=2",
    "SP-R 208": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/391.png?v=2",
    "SP-X 80": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/387.png?v=2",
    "STB 556": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/358.png?v=2",
    "TAQ-56": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/354.png?v=2",
    "TAQ-M": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/389.png?v=2",
    "TAQ-V": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/364.png?v=2",
    "TEMPUS RAZORBACK": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/418.png?v=2",
    "TEMPUS TORRENT": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/413.png?v=2",
    "TR-76 GEIST": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/tr_76.png",
    "VAZNEV-9K": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/373.png?v=2",
    "VEL 46": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/377.png?v=2",
    "VICTUS XMR": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/401.png?v=2",
    "X12": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/396.png?v=2",
    "X13 AUTO": "https://api.wzhub.gg/storage/uploads/loadouts/guns/default/398.png?v=2",
}
