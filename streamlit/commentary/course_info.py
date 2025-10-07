"""
Course information dictionary for TEG tournaments.
Contains facts, characteristics, and rankings for all courses played in TEG history.
"""

COURSE_INFO = {
    "Boavista": {
        "full_name": "Boavista Golf & Spa Resort",
        "location": "Lagos, Algarve, Portugal",
        "type": "Parkland",
        "par": 71,
        "designer": "Howard Swan",
        "opened": None,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "Two distinctive sections: Resort Section (holes 1-3, 13-18) and Country Section (holes 4-12)",
            "Signature hole: Par-4 7th with Atlantic Ocean views",
            "Panoramic ocean views"
        ],
        "rankings": "Featured in best Algarve golf course lists",
        "difficulty": "Championship course",
        "description": "A parkland course with stunning Atlantic Ocean views, designed by Howard Swan. The course splits into two distinct sections offering varied challenges."
    },

    "Ashdown": {
        "full_name": "Royal Ashdown Forest Golf Club (Old Course)",
        "location": "East Sussex, England",
        "type": "Heathland",
        "par": None,  # Par info not clearly stated in search
        "designer": None,
        "opened": 1888,
        "length_yards": 6537,
        "length_metres": None,
        "key_features": [
            "No bunkers on entire course - forbidden by Royal Forest charter",
            "732 feet above sea level in High Weald Area of Outstanding Natural Beauty",
            "Natural hazards: undulating land, streams, heather, bracken, trees",
            "Completely natural - no man-made alterations allowed"
        ],
        "rankings": "Ranked 31st in England by Golf World (2017)",
        "difficulty": "Championship - challenge from natural terrain",
        "description": "A unique heathland course with no bunkers, relying entirely on natural features for its challenge. Set high above sea level with spectacular views."
    },

    "Lingfield": {
        "full_name": "Lingfield Park Golf Club",
        "location": "Surrey, England",
        "type": "Parkland",
        "par": 72,
        "designer": "Harvey Jarrett",
        "opened": 1987,
        "length_yards": 6511,
        "length_metres": None,
        "key_features": [
            "Set in Surrey countryside within Lingfield Park Racecourse grounds",
            "Mature trees, ponds, and streams",
            "Panoramic views of Surrey landscape"
        ],
        "rankings": None,
        "difficulty": "Championship course - challenging for all abilities",
        "description": "A mature parkland course featuring grand trees and water hazards, offering a challenging but fair test in beautiful Surrey countryside."
    },

    "Crowborough": {
        "full_name": "Crowborough Beacon Golf Club",
        "location": "East Sussex, England",
        "type": "Heathland",
        "par": 71,  # GolfPass lists 71, though some sources say 72
        "designer": "Dr. Alister MacKenzie (redesigned 8 holes)",
        "opened": 1895,
        "length_yards": 6319,
        "length_metres": None,
        "key_features": [
            "800 feet above sea level on High Weald slopes",
            "Undulating fairways",
            "Spectacular views of South Downs and Ashdown Forest"
        ],
        "rankings": None,
        "difficulty": "Challenging with elevation changes",
        "description": "A classic heathland course at high elevation, with MacKenzie-designed holes and stunning panoramic views across the South Downs."
    },

    "Bletchingley": {
        "full_name": "Bletchingley Golf Club",
        "location": "Surrey, England",
        "type": "Parkland",
        "par": 72,
        "designer": "Paul Wright",
        "opened": 1993,
        "length_yards": 6600,
        "length_metres": None,
        "key_features": [
            "Fast-drying course - one of the quickest in the area",
            "Mature oak trees throughout",
            "Undulating fairways",
            "Views over North Downs and Weald",
            "Located on green-sand ridge"
        ],
        "rankings": None,
        "difficulty": "Firm and fast conditions - enjoyable challenge",
        "description": "A modern parkland course known for its excellent drainage and fast playing conditions. Features mature oaks and strategic design on undulating terrain."
    },

    "Palmares - Lagos / Praia": {
        "full_name": "Palmares Golf",
        "location": "Lagos, Algarve, Portugal",
        "type": "Parkland and Links",
        "par": None,  # 27-hole course with different combinations
        "designer": "Robert Trent Jones Jr.",
        "opened": None,
        "length_yards": None,
        "length_metres": 6905,  # Full 27-hole layout
        "key_features": [
            "27 holes in three 9-hole loops: Alvor (parkland), Lagos (parkland/lakes), Praia (links)",
            "Praia Loop: Pure links golf by the sea with dramatic dunes",
            "Lagos Loop: Mix of parkland and lakes leading to dunes",
            "Views of Bay of Lagos and Atlantic Ocean"
        ],
        "rankings": "Algarve favourite",
        "difficulty": "Requires adaptability - three distinct styles",
        "description": "A unique 27-hole resort combining parkland, lakeside and links golf. The Praia loop offers pure seaside links while Alvor and Lagos provide parkland challenges."
    },

    "Palmares - Praia / Alvor": {
        "full_name": "Palmares Golf",
        "location": "Lagos, Algarve, Portugal",
        "type": "Links and Parkland",
        "par": None,  # 27-hole course with different combinations
        "designer": "Robert Trent Jones Jr.",
        "opened": None,
        "length_yards": None,
        "length_metres": 6905,
        "key_features": [
            "27 holes in three 9-hole loops",
            "Alvor Loop: Parkland charm with hillside views and tree-lined fairways",
            "Praia Loop: Links golf by the sea",
            "Stunning Bay of Lagos and ocean views"
        ],
        "rankings": "Algarve favourite",
        "difficulty": "Varied - adaptability required",
        "description": "Different combination of the 27-hole Palmares layout, mixing the parkland Alvor nine with the dramatic seaside links of Praia."
    },

    "Palmares - Alvor / Lagos": {
        "full_name": "Palmares Golf",
        "location": "Lagos, Algarve, Portugal",
        "type": "Parkland",
        "par": None,
        "designer": "Robert Trent Jones Jr.",
        "opened": None,
        "length_yards": None,
        "length_metres": 6905,
        "key_features": [
            "Alvor: Parkland with hillside views",
            "Lagos: Parkland with lakes and dune transitions",
            "Tree-lined fairways on Alvor"
        ],
        "rankings": "Algarve favourite",
        "difficulty": "Strategic with water hazards",
        "description": "The most parkland-oriented combination at Palmares, featuring tree-lined fairways and strategic water hazards."
    },

    "PGA Catalunya - Tour": {
        "full_name": "Camiral Golf & Wellness - Tour Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Parkland",
        "par": None,  # Par not specified in search results
        "designer": "Angel Gallardo and Neil Coles (European Tour design)",
        "opened": None,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "Shorter and less difficult than Stadium Course",
            "Top-notch golfing experience",
            "Part of #1 rated resort in Spain"
        ],
        "rankings": "Ranked in Spanish Top 100",
        "difficulty": "Challenging but less stern than Stadium",
        "description": "The second championship course at PGA Catalunya Resort, offering excellent golf in a slightly more forgiving layout than its famous Stadium sibling."
    },

    "PGA Catalunya - Stadium": {
        "full_name": "Camiral Golf & Wellness - Stadium Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Championship Parkland",
        "par": 72,
        "designer": "Angel Gallardo and Neil Coles (European Tour)",
        "opened": 1998,
        "length_yards": 8049,  # 7333 yards = approx 6704m
        "length_metres": 7333,
        "key_features": [
            "Designed by European Tour as championship test",
            "Hosted European Tour events",
            "Challenging layout requiring strategic play"
        ],
        "rankings": "5th in Continental Europe (Golf World), #1 in Spain, World Top 100",
        "difficulty": "Championship - highest level",
        "description": "Spain's premier golf course, designed by the European Tour. A world-class championship test that has hosted professional tournaments and consistently ranks among Europe's elite."
    },

    "Costa Brava": {
        "full_name": "Club de Golf Costa Brava",
        "location": "Catalonia, Spain",
        "type": "Parkland/Woodland",
        "par": 70,
        "designer": "John Hamilton Stutt (original), Jorge Soler Peix (new holes)",
        "opened": 1968,  # Course appeared 6 years after 1962 founding
        "length_yards": None,
        "length_metres": 5573,
        "key_features": [
            "Front nine through woods with pine trees and cork oaks",
            "More open back nine",
            "Technical first nine with narrow fairways and mounds",
            "More relaxed second nine",
            "9 new holes added in 2004 creating Red/Green configurations"
        ],
        "rankings": None,
        "difficulty": "Technical front nine, relaxed back nine",
        "description": "A woodland parkland course with contrasting nines - a technical tree-lined front nine followed by a more open and relaxed back nine."
    },

    "El Prat - Rosa": {
        "full_name": "Real Club de Golf El Prat - Rosa (Pink) Course",
        "location": "Barcelona, Catalonia, Spain",
        "type": "Parkland",
        "par": 72,
        "designer": "Greg Norman (45 holes total)",
        "opened": None,
        "length_yards": None,
        "length_metres": 6492,
        "key_features": [
            "Part of 45-hole complex (three 18-hole configurations)",
            "Hosted Spanish Open 10 times",
            "Greg Norman design emphasizing comfort and beauty",
            "Harmoniously integrated with nature"
        ],
        "rankings": "13th best course in Spain",
        "difficulty": "Championship - adaptable to different skill levels",
        "description": "The most prestigious of El Prat's three 18-hole configurations. A Greg Norman design that has hosted the Spanish Open multiple times."
    },

    "El Prat - Azul": {
        "full_name": "Real Club de Golf El Prat - Azul Course",
        "location": "Barcelona, Catalonia, Spain",
        "type": "Parkland",
        "par": 72,
        "designer": "Greg Norman",
        "opened": None,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "Part of 45-hole Greg Norman complex",
            "Three color-coded 18-hole courses: Rosa, Amarillo, Verde",
            "Strategic design integrated with natural landscape"
        ],
        "rankings": None,
        "difficulty": "Championship level",
        "description": "Note: El Prat has three courses - Rosa (Pink), Amarillo (Yellow), and Verde (Green). 'Azul' (Blue) may refer to one of these configurations or a routing variation."
    },

    "Praia D'El Rey": {
        "full_name": "Praia D'El Rey Golf & Beach Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Links and Parkland",
        "par": 73,
        "designer": "Cabell B. Robinson",
        "opened": 1997,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "Front 9: Parkland style",
            "Back 9: Links with blown-out dunes and wide fairways",
            "One hour northwest of Lisbon on Silver Coast",
            "Near medieval town of Óbidos"
        ],
        "rankings": "Top 60 in Continental Europe, Top 10 in Portugal, GOLF's Top 100 Resorts Worldwide",
        "difficulty": "Championship",
        "description": "A spectacular course mixing parkland and links golf, with the back nine featuring dramatic coastal dunes. Highly ranked in European and world golf."
    },

    "Bom Sucesso": {
        "full_name": "Guardian Bom Sucesso Golf",
        "location": "Caldas da Rainha/Obidos, Lisbon Coast, Portugal",
        "type": "Parkland",
        "par": 72,
        "designer": "Donald Steel (Martin Ebert as lead architect)",
        "opened": 2008,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "Alongside Lagoa de Óbidos",
            "Front nine on flat terrain",
            "Back nine on hilly ground with engaging views",
            "Long greens, lakes, and strategic bunkers"
        ],
        "rankings": None,
        "difficulty": "Championship with varied terrain",
        "description": "A Donald Steel design featuring contrasting nines - flat opening nine followed by hillier back nine with spectacular lagoon views."
    },

    "Royal Óbidos": {
        "full_name": "Royal Obidos Spa & Golf Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Parkland",
        "par": 72,
        "designer": "Seve Ballesteros",
        "opened": 2012,
        "length_yards": 7421,  # 6765m converted
        "length_metres": 6765,
        "key_features": [
            "Significant water hazards on six holes",
            "Lakes interconnected by cascading streams",
            "Signature 5th hole: 520m Par 5 with approach to island green",
            "12th hole: 420m Par 4 negotiating water twice",
            "Seve's final design (died before completion)"
        ],
        "rankings": "Hosts European Challenge Tour - Open de Portugal (since 2020)",
        "difficulty": "Championship - strategic water hazards",
        "description": "Seve Ballesteros' final course design, a challenging championship layout with dramatic water features. Hosts European Challenge Tour events."
    },

    "Quinta da Marinha": {
        "full_name": "Quinta da Marinha Golf Course",
        "location": "Cascais, Estoril Coast, Portugal",
        "type": "Parkland",
        "par": 71,
        "designer": "Robert Trent Jones Sr.",
        "opened": None,
        "length_yards": None,
        "length_metres": 5870,
        "key_features": [
            "25km from Lisbon on Estoril Coast",
            "Elevated greens and tees",
            "Many bunkers and water hazards",
            "Views over Atlantic Ocean and Sintra Mountains",
            "Signature 5th: Par 3 over large lake",
            "Spectacular 13th: Par 4 sloping down to sea",
            "Set in 110-hectare pine forest estate"
        ],
        "rankings": None,
        "difficulty": "Strategic - elevated targets and hazards",
        "description": "A classic Robert Trent Jones Sr. design featuring elevated targets, abundant bunkering, and spectacular ocean views. Set within a private pine forest estate."
    },

    "Penha Longa": {
        "full_name": "The Ritz-Carlton Penha Longa - Atlantic Course",
        "location": "Sintra, Lisbon Coast, Portugal",
        "type": "Mountain Parkland",
        "par": 72,
        "designer": "Robert Trent Jones Jr.",
        "opened": 1992,
        "length_yards": 6313,
        "length_metres": None,
        "key_features": [
            "Set in Sintra Mountains (Sintra Cascais Nature Park)",
            "Steeply sloping terrain",
            "Views of Estoril, Cascais, and Atlantic Ocean",
            "Woodland and hillside sections",
            "Also features 9-hole Mosteiro course"
        ],
        "rankings": "26th Best Value Course Worldwide (2024), Top 10 in Portugal",
        "difficulty": "Brutal - steep slopes and elevation changes",
        "description": "A dramatic mountain course in the Sintra hills, known for its steep terrain and breathtaking coastal views. Considered one of Portugal's most challenging layouts."
    },

    "Oitavos Dunes": {
        "full_name": "Oitavos Dunes Natural Links Golf",
        "location": "Cascais, Lisbon Coast, Portugal",
        "type": "Links",
        "par": 71,
        "designer": "Arthur Hills",
        "opened": 2001,
        "length_yards": None,
        "length_metres": 6300,
        "key_features": [
            "In Sintra-Cascais National Park",
            "Natural sand dunes",
            "Old-fashioned out-and-back routing",
            "Atlantic coastline setting",
            "First European course with Audubon Gold Certification",
            "Hosted four Portuguese Opens",
            "Pure links experience"
        ],
        "rankings": "#1 in Portugal, 55th Worldwide (Golf Magazine), Top 100 Worldwide",
        "difficulty": "Championship links - wind exposure",
        "description": "Portugal's premier golf course, a pure links design along the rugged Atlantic coast. Features natural dunes and has hosted multiple Portuguese Opens."
    },

    "Royal Cinque Ports": {
        "full_name": "Royal Cinque Ports Golf Club",
        "location": "Deal, Kent, England",
        "type": "Links",
        "par": 71,  # Yellow tees; 72 from tips
        "designer": None,
        "opened": None,
        "length_yards": 6500,  # Yellow tees; 7300+ from tips
        "length_metres": None,
        "key_features": [
            "Often known simply as 'Deal'",
            "Hosted The Open Championship 1909 and 1920",
            "Brutal back nine into prevailing south-westerly wind",
            "Classic British links"
        ],
        "rankings": "43rd in UK&I (Golf Monthly), Golf World Top 100 Worldwide",
        "difficulty": "Very stiff challenge - especially back nine",
        "description": "A formidable championship links that hosted two Open Championships. Known as one of the toughest tests on the Kent coast, particularly when the wind blows."
    },

    "Prince's - Dunes / Himalayas": {
        "full_name": "Prince's Golf Club",
        "location": "Sandwich, Kent, England",
        "type": "Links",
        "par": 36,  # Each nine is par 36
        "designer": "Mackenzie and Ebert (Himalayas redesign)",
        "opened": None,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "27 holes in three loops: Shore, Dunes, Himalayas",
            "Hosted 1932 Open Championship",
            "To host 2030 Walker Cup",
            "Deep bunkers, undulating fairways, tricky greens",
            "Naturally sculpted links",
            "Himalayas nine recently redesigned by Mackenzie & Ebert"
        ],
        "rankings": "Top 100 (various combinations)",
        "difficulty": "Championship links - complete test of golf",
        "description": "A 27-hole championship links offering authentic, classic links golf. Hosted the Open Championship and will host the 2030 Walker Cup. Three superb nines combine in various configurations."
    },

    "Prince's - Shore / Dunes": {
        "full_name": "Prince's Golf Club",
        "location": "Sandwich, Kent, England",
        "type": "Links",
        "par": 72,  # 36 + 36
        "designer": "Various; Mackenzie & Ebert recent work",
        "opened": None,
        "length_yards": None,
        "length_metres": None,
        "key_features": [
            "27 holes in three loops",
            "Shore nine follows coastline",
            "Shore is longest of the three nines",
            "Natural sand dunes and links terrain",
            "Deep bunkers and undulating fairways"
        ],
        "rankings": "Considered the best 18-hole combination at Prince's",
        "difficulty": "Championship links",
        "description": "The classic combination at Prince's, pairing the coastal Shore nine with the Dunes nine for an outstanding links experience. Considered the strongest routing."
    },

    "Littlestone": {
        "full_name": "Littlestone Golf Club - Championship Links",
        "location": "Littlestone-on-Sea, Kent, England",
        "type": "Links",
        "par": 71,
        "designer": "William Laidlaw Purves (same as Royal St George's), refined by James Braid and Alister MacKenzie",
        "opened": 1888,
        "length_yards": 6632,
        "length_metres": None,
        "key_features": [
            "On Romney Marshes with English Channel backdrop",
            "Remote classic links location",
            "Impressive design pedigree",
            "Natural undulating links terrain"
        ],
        "rankings": "65th in England (Golf World 2024), 148th in Britain & Ireland (2025)",
        "difficulty": "Championship links",
        "description": "A classic remote links course on the Romney Marshes, designed by the architect of Royal St George's and refined by Braid and MacKenzie. True championship test."
    },

    "Estoril": {
        "full_name": "Estoril Golf Club",
        "location": "Estoril, Cascais, Portugal",
        "type": "Parkland",
        "par": 69,
        "designer": "Mackenzie Ross (redesign 1936)",
        "opened": 1929,  # Original opening
        "length_yards": None,
        "length_metres": 5233,
        "key_features": [
            "First golf club in Portugal",
            "25 minutes from Lisbon",
            "Set among eucalyptus, pine, and mimosa trees",
            "Uneven terrain",
            "Emphasis on accuracy over distance"
        ],
        "rankings": None,
        "difficulty": "Strategic - accuracy required",
        "description": "Portugal's first golf club, a shorter classic parkland course emphasizing accuracy and course management. Charming tree-lined layout redesigned by Mackenzie Ross."
    },

    "West Cliffs": {
        "full_name": "West Cliffs Golf Links",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Links",
        "par": 72,
        "designer": "Cynthia Dye",
        "opened": 2017,
        "length_yards": None,
        "length_metres": 6382,
        "key_features": [
            "Natural links among sand dunes",
            "Ocean views",
            "Silver Coast location, one hour north of Lisbon",
            "Natural links-style layout"
        ],
        "rankings": "World's Best New Course 2017, broke into Top 25 in Europe, Top 25 Best Courses in Portugal",
        "difficulty": "Championship links",
        "description": "A spectacular modern links design that won 'World's Best New Course' in 2017. Natural dune landscape with ocean views on Portugal's Silver Coast."
    },

    "Troia": {
        "full_name": "Troia Golf Championship Course",
        "location": "Troia Peninsula, Setubal, Portugal",
        "type": "Championship Course",
        "par": 72,
        "designer": "Robert Trent Jones Sr.",
        "opened": None,
        "length_yards": None,
        "length_metres": 6317,
        "key_features": [
            "40km south of Lisbon on peninsula",
            "Accessible by ferry from Setubal",
            "Hole 3 selected by RTJ Sr. as one of his best designs",
            "Coastal setting"
        ],
        "rankings": "8th in Continental Europe (Golf World 2019), 17th in Continental Europe (2018), Rolex World's Top 1,000 (2011)",
        "difficulty": "Championship - world-class test",
        "description": "A prestigious Robert Trent Jones Sr. design on the Troia Peninsula. Consistently ranked among Europe's finest courses, featuring RTJ's signature strategic design."
    }
}
