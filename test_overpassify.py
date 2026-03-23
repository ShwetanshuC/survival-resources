from overpassify import overpassify

radius = 2000
lat = 40.7128
lon = -74.006

code = f"""
def dummy():
    my_nodes = Node(Around({radius}, {lat}, {lon}), amenity=Regex('hospital|clinic|doctors'))
    out(my_nodes, qt=True)
"""
try:
    query_str = overpassify(code.strip())
    query_str = query_str.replace('""', '"')
    final_query = "[out:json];\\n" + query_str
    print("Final Query:\\n", final_query)
except Exception as e:
    import traceback
    traceback.print_exc()
