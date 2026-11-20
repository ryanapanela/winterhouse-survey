"""Survey item metadata for the analysis tools.

Mirrors docs/questions.js (generated from it on 2026-11-20). If you change an id,
a word, or a block letter there, change it here too.
"""
HOST = "Ryan"  # hosts Traitors, so he is never a target of Traitors questions
AWAY = ["Jesse"]  # in the network but not at the cottage: not in Traitors or weekend-only picks
NON_PLAYERS = [HOST] + AWAY
WEEKEND_ONLY = ["D13", "E03", "E07"]

LIKERT_IDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19", "B20", "B21", "B22", "B23", "B24", "B25", "B26", "B27", "B28", "B29", "B30", "B52"]
TOT_IDS = ["B31", "B32", "B33", "B34", "B35", "B36", "B37", "B38", "B39", "B40", "B41", "B42", "B43", "B44", "B45", "B46", "B47", "B48", "B49", "B50", "B51"]
ITEM_TEXT = {
 "B01": "Honesty beats kindness when the two conflict.",
 "B02": "Work-life balance matters more to me than moving fast in my career.",
 "B03": "I'd move countries for the right job.",
 "B04": "Money matters more to me than I usually admit.",
 "B05": "I believe things happen for a reason.",
 "B06": "I'd rather be respected than liked.",
 "B07": "Ambition is one of my defining traits.",
 "B08": "I could lie convincingly to this group for four days.",
 "B09": "I'd tell a friend if I thought their partner was bad news.",
 "B10": "Gossip brings people closer.",
 "B11": "I hold grudges.",
 "B12": "Texting back quickly is a sign of respect.",
 "B13": "I'd rather deal with a conflict right away than let it cool off.",
 "B14": "Splitting the bill evenly is fair, whatever people ordered.",
 "B15": "Group chats should have rules.",
 "B16": "Being late is disrespectful.",
 "B17": "I recharge best alone.",
 "B18": "I'm usually the one who plans the group hangout.",
 "B19": "I'm easily embarrassed.",
 "B20": "I'd sing karaoke completely sober.",
 "B21": "I'm a better listener than talker.",
 "B22": "I care what strangers think of me.",
 "B23": "I would cry in public.",
 "B24": "Academia is worth it.",
 "B25": "I'll stay in research after the PhD.",
 "B26": "Reviewer 2 is usually right.",
 "B27": "I do my best work at the last minute.",
 "B28": "I'd pick a famous lab over a kind supervisor.",
 "B29": "Conferences are mostly about the socials.",
 "B30": "I could explain my thesis to a 10-year-old.",
 "B31": "Plan the trip · Wing it",
 "B32": "Host · Be hosted",
 "B33": "Morning person · Night person",
 "B34": "Dogs · Cats",
 "B35": "Board games are ruthless · Board games are friendly",
 "B36": "Comfortable silence in the car · Keep the conversation going",
 "B37": "Big group dinner · Deep one-on-one",
 "B38": "Reality TV is a guilty pleasure · Reality TV is high art",
 "B39": "Text · Call",
 "B40": "Lake swim · Hot tub",
 "B41": "Spoilers don't bother me · Spoilers ruin everything",
 "B42": "I'd rather be a Traitor · I'd rather be a Faithful",
 "B43": "Sweet · Savoury",
 "B44": "Cook · Clean up",
 "B45": "Mountains · Beach",
 "B46": "Early to the party · Fashionably late",
 "B47": "Know the future · Change the past",
 "B48": "Head, for big decisions · Heart, for big decisions",
 "B49": "Be famous · Be powerful",
 "B50": "Read the whole group chat · Skim and react",
 "B51": "Pho · Ramen",
 "B52": "Friends are just as valuable as a romantic partner."
}
BLOCKS = {"A": ["B01", "B09", "B17", "B24", "B31", "B42"], "B": ["B03", "B10", "B19", "B25", "B33", "B43"], "C": ["B04", "B11", "B20", "B26", "B35", "B46"], "D": ["B06", "B13", "B23", "B27", "B37", "B48"]}  # prediction-game item blocks

WORDS = {
 "faithful": [
  "Loyal",
  "Honest",
  "Reliable",
  "Warm",
  "Generous",
  "Open"
 ],
 "traitor": [
  "Strategic",
  "Mysterious",
  "Persuasive",
  "Observant",
  "Sharp",
  "Unpredictable"
 ],
 "fun": [
  "Hilarious",
  "Chaotic",
  "Dramatic",
  "Spontaneous",
  "Sarcastic",
  "Bold"
 ],
 "steady": [
  "Calm",
  "Thoughtful",
  "Grounded",
  "Organized",
  "Curious",
  "Diplomatic"
 ]
}
WORD_CODE = {w: cat for cat, ws in WORDS.items() for w in ws}

# (id, question, max picks, excludes host)
D_QS = [
 [
  "D01",
  "If something went wrong at 2am, who here would you call?",
  3,
  False
 ],
 [
  "D02",
  "Who do you go to for advice on research or career decisions?",
  2,
  False
 ],
 [
  "D03",
  "Who would you trust with a secret?",
  2,
  False
 ],
 [
  "D04",
  "Who here understands you best?",
  1,
  False
 ],
 [
  "D05",
  "Who would you like to get to know better?",
  3,
  False
 ],
 [
  "D06",
  "Who makes you laugh the most?",
  2,
  False
 ],
 [
  "D07",
  "Who would you want on your team for a mission?",
  2,
  False
 ],
 [
  "D08",
  "Who would you want next to you on a 5-hour drive?",
  1,
  False
 ],
 [
  "D09",
  "Who would you go to for a hype-up before a big talk?",
  1,
  False
 ],
 [
  "D10",
  "Who are you suspicious of before the game even starts?",
  2,
  True
 ],
 [
  "D11",
  "If you were a Traitor, who would you want as your fellow Traitor?",
  1,
  True
 ],
 [
  "D13",
  "Who will surprise everyone this weekend?",
  1,
  False
 ]
]
# (id, question, "pair" | "person", count, excludes host)
E_QS = [
 [
  "E01",
  "Which pairs in the group are closest?",
  "pair",
  3,
  False
 ],
 [
  "E02",
  "Unexpected Pairing, the classic: which pair gets along far better than anyone would have guessed?",
  "pair",
  2,
  False
 ],
 [
  "E03",
  "Unexpected Pairing you hope to see this weekend: which two people do you think would be great together?",
  "pair",
  2,
  False
 ],
 [
  "E06",
  "Which pair would make the best secret Traitor duo?",
  "pair",
  1,
  True
 ],
 [
  "E07",
  "Which pair would you most want to watch do a confessional together?",
  "pair",
  1,
  False
 ],
 [
  "E10",
  "Who in this group has grown the most over the last five years?",
  "person",
  1,
  False
 ]
]
# (id, award, excludes host)
G_QS = [
 [
  "G01",
  "Most Likely to Become a Prof",
  False
 ],
 [
  "G14",
  "Worst Case of Senioritis",
  False
 ],
 [
  "G27",
  "Teacher's Pet",
  False
 ],
 [
  "G22",
  "Whose Supervisor Is the Most Eccentric?",
  False
 ],
 [
  "G06",
  "Best Smile",
  False
 ],
 [
  "G07",
  "Best Hair",
  False
 ],
 [
  "G08",
  "Best Laugh",
  False
 ],
 [
  "G09",
  "Best Dressed (Everyday)",
  False
 ],
 [
  "G10",
  "Most Photogenic",
  False
 ],
 [
  "G11",
  "Most Athletic",
  False
 ],
 [
  "G12",
  "Most Artistic",
  False
 ],
 [
  "G28",
  "Most Secret Talents",
  False
 ],
 [
  "G04",
  "Class Clown",
  False
 ],
 [
  "G13",
  "Social Butterfly",
  False
 ],
 [
  "G15",
  "Biggest Flirt",
  False
 ],
 [
  "G16",
  "Most Likely to Become a Reality Star",
  False
 ],
 [
  "G17",
  "Most Likely to Get Married Next",
  False
 ],
 [
  "G23",
  "Most Likely to Win a German Drinking Game",
  False
 ],
 [
  "G19",
  "Worst Aux Cord Privileges",
  False
 ],
 [
  "G20",
  "Most Tardy",
  False
 ],
 [
  "G21",
  "Most Sneaky / Best Deceiver",
  False
 ],
 [
  "G24",
  "Most Controversial",
  False
 ],
 [
  "G25",
  "Most Likely to Have an OnlyFans",
  False
 ],
 [
  "G26",
  "Most Likely to Go to Jail for White-Collar Crime",
  False
 ],
 [
  "G29",
  "Most Likely to Leave the Country and Never Be Seen Again",
  False
 ],
 [
  "G30",
  "Most Likely to Marry for a Visa",
  False
 ],
 [
  "G31",
  "Most Likely to Live a Double Life",
  False
 ],
]
SUPPORT_QS = ["D01", "D02", "D03", "D04"]
