# Écritures de signalisation : Inde, Bangladesh, Sri Lanka.
# Faits reformulés à partir de Plonk It (Inde, Sri Lanka) + connaissances générales ; aucune image ni texte copié.
SCRIPTS = [
  # key, label, color, sample, sample font, where, cue
  ("deva",  "Devanagari (hindi)",   "#e5a54b", "दिल्ली",     "deva", "Nord et centre de l'Inde",                "Barre continue au-dessus du mot, traits verticaux"),
  ("mar",   "Devanagari (marathi)", "#b86a2c", "कळंबोली",    "deva", "Maharashtra, Goa (konkani)",              "Même écriture ; la lettre ळ (absente en hindi) trahit le marathi"),
  ("nep",   "Devanagari (népalais)","#f0d29a", "गान्तोक",    "deva", "Sikkim (et Népal)",                       "Même écriture, contexte himalayen"),
  ("guru",  "Gurmukhi",             "#e9d64e", "ਅੰਮ੍ਰਿਤਸਰ",  "guru", "Punjab",                                  "Barre du haut interrompue, lettres plus carrées et douces"),
  ("guj",   "Gujarati",             "#e0706a", "અમદાવાદ",    "guj",  "Gujarat, Daman-et-Diu",                   "Comme le devanagari, mais sans barre au-dessus"),
  ("urdu",  "Ourdou (arabe)",       "#8fa3b3", "سرینگر",     "arab", "Jammu-et-Cachemire, Ladakh",              "Écriture arabe, de droite à gauche"),
  ("beng",  "Bengali",              "#3f9f66", "কলকাতা",     "beng", "Bengale-Occidental, Tripura, Bangladesh", "Triangles pointés vers la gauche, barre au-dessus"),
  ("asm",   "Assamais",             "#86d6ad", "গুৱাহাটী",    "beng", "Assam",                                   "Alphabet bengali + ৰ (r barré) et ৱ (w)"),
  ("odia",  "Odia",                 "#33b5ad", "ଭୁବନେଶ୍ୱର",   "orya", "Odisha",                                  "Grand arc arrondi coiffant chaque lettre"),
  ("telu",  "Télougou",             "#5c8fdc", "హైదరాబాద్",   "telu", "Andhra Pradesh, Telangana",               "Lettres rondes, petites coches ✓ au sommet"),
  ("knda",  "Kannada",              "#9c7ee2", "ಬೆಂಗಳೂರು",    "knda", "Karnataka",                               "Proche du télougou, sans coche ; crochet en haut à droite"),
  ("taml",  "Tamoul",               "#d75fa9", "சென்னை",     "taml", "Tamil Nadu, Puducherry ; nord et est du Sri Lanka", "Angles droits, peu de courbes, points au-dessus (pulli)"),
  ("mlym",  "Malayalam",            "#c4da4f", "കൊച്ചി",      "mlym", "Kerala, Lakshadweep",                     "Boucles en U renversé, lettres liées"),
  ("mtei",  "Meitei Mayek",         "#e35353", "ꯏꯝꯐꯥꯜ",      "mtei", "Manipur",                                 "Traits verticaux et angles droits"),
  ("latn",  "Latin (mizo, anglais)","#d9e1e6", "Aizawl",     "latn", "Mizoram (mizo), Meghalaya, Nagaland, Arunachal (anglais)", "Seule région de l'Inde où le latin domine"),
  ("sinh",  "Cinghalais",           "#57c7e3", "කොළඹ",       "sinh", "Tout le Sri Lanka (propre au pays)",      "Tout en boucles, comme des bulles"),
]
IN = {
 "Uttar Pradesh":"deva","Bihar":"deva","Madhya Pradesh":"deva","Rajasthan":"deva","Haryana":"deva","Delhi":"deva",
 "Uttarakhand":"deva","Himachal Pradesh":"deva","Jharkhand":"deva","Chhattisgarh":"deva","Chandigarh":"deva",
 "Andaman and Nicobar":"deva","Maharashtra":"mar","Goa":"mar","Sikkim":"nep","Punjab":"guru","Gujarat":"guj",
 "Dadra and Nagar Haveli and Daman and Diu":"guj","Jammu and Kashmir":"urdu","Ladakh":"urdu","West Bengal":"beng",
 "Tripura":"beng","Assam":"asm","Odisha":"odia","Andhra Pradesh":"telu","Telangana":"telu","Karnataka":"knda",
 "Tamil Nadu":"taml","Puducherry":"taml","Kerala":"mlym","Lakshadweep":"mlym","Manipur":"mtei","Mizoram":"latn",
 "Meghalaya":"latn","Nagaland":"latn","Arunachal Pradesh":"latn",
}
LK_TAMIL = {"Yāpanaya","Kilinŏchchi","Mannārama","Mulativ","Vavuniyāva","Maḍakalapuva"}
LK_MIXED = {"Trikuṇāmalaya","Ampāra","Nuvara Ĕliya"}
NOTES = [
  ("Bangladesh ou Bengale-Occidental ?", "Même écriture. Au Bangladesh, les panneaux sont souvent en bengali seul ; en Inde, le bengali côtoie volontiers l'anglais ou l'hindi."),
  ("Tamoul : Inde ou Sri Lanka ?", "Au Sri Lanka, le tamoul seul indique le nord ou l'est ; les panneaux bilingues cinghalais–tamoul existent partout dans l'île. Poche tamoule aussi autour de Nuwara Eliya (plantations de thé)."),
]
LABELS = [  # (key, lon, lat, texte)
  ("deva",78.5,25.0,"Hindi"),("mar",75.8,19.2,"Marathi"),("guru",75.4,30.8,"Gurmukhi"),("guj",70.9,22.0,"Gujarati"),
  ("urdu",76.6,35.0,"Ourdou"),("beng",87.9,23.6,"Bengali"),("beng",89.35,24.05,"Bengali (BD)"),("asm",93.3,26.55,"Assamais"),
  ("odia",84.3,20.4,"Odia"),("telu",79.6,16.2,"Télougou"),("knda",75.9,14.6,"Kannada"),("taml",78.4,11.0,"Tamoul"),
  ("mlym",76.0,11.45,"Malayalam"),("mtei",94.25,24.25,"Meitei"),("latn",94.4,27.9,"Latin"),
]

# Villes principales : (lon, lat, nom, côté de l'étiquette r/l)
CITIES = [
  (77.21,28.61,"Delhi","r"),(72.88,19.08,"Mumbai","l"),(88.36,22.57,"Kolkata","l"),(80.27,13.08,"Chennai","r"),
  (77.59,12.97,"Bengaluru","r"),(78.49,17.39,"Hyderabad","r"),(72.57,23.02,"Ahmedabad","r"),(73.86,18.52,"Pune","r"),
  (75.79,26.91,"Jaipur","r"),(80.95,26.85,"Lucknow","r"),(85.14,25.59,"Patna","r"),(77.41,23.26,"Bhopal","r"),
  (79.09,21.15,"Nagpur","r"),(85.82,20.30,"Bhubaneswar","r"),(91.74,26.14,"Guwahati","l"),(74.80,34.08,"Srinagar","l"),
  (77.58,34.15,"Leh","r"),(74.87,31.63,"Amritsar","l"),(76.78,30.73,"Chandigarh","r"),(78.03,30.32,"Dehradun","r"),
  (82.97,25.32,"Varanasi","r"),(81.63,21.25,"Raipur","r"),(85.31,23.34,"Ranchi","r"),(83.22,17.69,"Visakhapatnam","r"),
  (78.12,9.93,"Madurai","r"),(76.27,9.93,"Kochi","l"),(76.94,8.52,"Thiruvananthapuram","l"),(74.86,12.91,"Mangaluru","l"),
  (73.83,15.49,"Panaji","l"),(93.94,24.82,"Imphal","r"),(91.89,25.58,"Shillong","l"),(92.72,23.73,"Aizawl","r"),
  (88.61,27.33,"Gangtok","r"),(90.41,23.81,"Dhaka","r"),(91.83,22.36,"Chattogram","r"),
  (91.87,24.89,"Sylhet","r"),(89.56,22.82,"Khulna","r"),(92.73,11.62,"Port Blair","r"),
]
CITIES_LK = [
  (79.86,6.93,"Colombo","r"),(80.01,9.66,"Jaffna","r"),(80.64,7.29,"Kandy","r"),(81.23,8.59,"Trincomalee","r"),
  (81.69,7.73,"Batticaloa","l"),(80.22,6.05,"Galle","r"),(80.41,8.31,"Anuradhapura","r"),
]
