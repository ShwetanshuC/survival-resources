from overpassify import overpassify, Node, Around, Regex

radius = 25000
lat = 40.7128
lon = -74.0060

code = f"""
def dummy():
    my_nodes = Node(Around({radius}, {lat}, {lon}), **{{'\"amenity\"': Regex('hospital|clinic|doctors')}})
    out(my_nodes, qt=True)
"""
try:
    query_str = overpassify(code.strip())
    query_str = query_str.replace('""', '"')
    final_query = "[out:json];\\n" + query_str
    print("Final Query:\\n", final_query)
except Exception as e:
    print("Error:", e)
