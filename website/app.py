from flask import Flask, render_template, request, url_for
import os
import folium
import webbrowser
from PIL import Image
import io
import pandas as pd
import numpy as np

# find current directory for app.py
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")

stations_path = os.path.join(base_dir, "..", "data", "stations.csv")
routes_path = os.path.join(base_dir, "..", "data", "routes.csv")
lineColours_path = os.path.join(base_dir, "..", "data", "routeColours.csv")

# get network data
stations = pd.read_csv(stations_path)
routes = pd.read_csv(routes_path)
lineColours = pd.read_csv(lineColours_path)

# plot points on map representing each station
def plotStations(map, stations, routes):
    for index, station in stations.iterrows():
        location = [station["latitude"], station["longitude"]]
        folium.CircleMarker(location, radius=3,
                       popup = f"Station:{station["station"]}",
                       color="green",
                       fill_color="#000000",
                       fill_opacity=1.0,
                       weight=2).add_to(map)

# draw the connections between stations
def plotTrainConnections(map, stations, routes):
    for index, route in routes.iterrows():
        # get names of stations
        station1 = stations[stations.station==route["von"]]
        station2 = stations[stations.station==route["nach"]]
    
        # get coordinates of stations
        coords1 = [station1["latitude"].iloc[0], station1["longitude"].iloc[0]]
        coords2 = [station2["latitude"].iloc[0], station2["longitude"].iloc[0]]

        # get colour based on rail line
        line = route["linie"]
        lineColour = lineColours[lineColours.route==line]
        lineColourStr = "rgb("+str(lineColour.r.item())+", "+str(lineColour.g.item())+", "+str(lineColour.b.item())+")"

        # add line to map
        folium.PolyLine([coords1, coords2], color=lineColourStr, weight=2.5, opacity=0.8).add_to(map)

def generateImage(map, imageName="myImage.png", saveImg=True):
    img_data = map._to_png(5) # 5 second delay to let tiles load
    img = Image.open(io.BytesIO(img_data))
    if saveImg:
        img.save(imageName)
    return img

def extractTrainline(stations, routes, line):
    # extract routes just on that line
    trainLine = routes[routes.linie == line]

    # get all station names on that line
    stationNames = set()
    for index, row in trainLine.iterrows():
        stationNames.add(str(row.von))
        stationNames.add(str(row.nach))
    stationNames = list(stationNames)
        
    # extract stations just on that line
    stationsSubset = stations[stations.station.isin(stationNames)]

    return stationsSubset, trainLine

def extractAllLinesAroundStation(stations, routes, stationName):
    # find all connections containing station
    df1 = routes[routes["von"].str.contains(stationName)]
    df2 = routes[routes["nach"].str.contains(stationName)]
    df = pd.concat([df1, df2], axis=0)

    # extract all lines that station is on
    lines = list(df.linie.unique())

    # get all network data from each train line
    stationsSubsetAll = []
    trainLineSubsetAll = []

    for line in lines:
        stationsSubset, trainLine = extractTrainline(stations, routes, line)
        stationsSubsetAll.append(stationsSubset)
        trainLineSubsetAll.append(trainLine)
    
    stationsSubsetAll = pd.concat(stationsSubsetAll, axis=0)
    trainLineSubsetAll = pd.concat(trainLineSubsetAll, axis=0)
    
    return stationsSubsetAll, trainLineSubsetAll

### WEB APPLICATION ###
app = Flask(__name__)

@app.route("/")
def index():
    map_path = url_for("static", filename="map.html")
    return render_template("index.html", map_url=map_path)

@app.route("/process", methods=["POST"])
def process():
    # get input from HTML
    line = request.form["station-name-input"].strip()

    # protect against harmful input
    if not line.isalnum():
        map_path = url_for("static", filename="map.html")
        return render_template("index.html", error="Invalid input", map_url=map_path)

    # the S41 has bee excluded from the dataset because it has the same stations and routes as the S42
    allBerlinLines = list(routes.linie.unique())
    allBerlinLines.append("S41")
    if line.upper() == "S41":
        line = "S42"
    
    # if input is a station name it's handeled here
    allBerlinStations = list(stations.station.unique())

    if line.upper() == "ALL":
        map_path = url_for("static", filename="map.html")
        return render_template("index.html", map_url=map_path)
    
    elif line in allBerlinStations:
        # generate new map
        m_sub = folium.Map(tiles="cartodb positron", location=(52.52, 13.40), zoom_start=10)
        subS, subR = extractAllLinesAroundStation(stations, routes, line)
        plotStations(m_sub, subS, subR)
        plotTrainConnections(m_sub, subS, subR)
        map_path = os.path.join(static_dir, "map-subset.html")
        m_sub.save(map_path)

        # render page with new map
        generated_map_url = url_for('static', filename='map-subset.html')
        return render_template("index.html", map_url=generated_map_url)
    
    elif line.upper() in allBerlinLines:
        # generate new map
        m_sub = folium.Map(tiles="cartodb positron", location=(52.52, 13.40), zoom_start=10)
        subS, subR = extractTrainline(stations, routes, line.upper())
        plotStations(m_sub, subS, subR)
        plotTrainConnections(m_sub, subS, subR)
        map_path = os.path.join(static_dir, "map-subset.html")
        m_sub.save(map_path)

        # render page with new map
        generated_map_url = url_for('static', filename='map-subset.html')
        return render_template("index.html", map_url=generated_map_url)

    else:
        map_path = url_for("static", filename="map.html")
        return render_template("index.html", error="That is not a Berlin train line or station.", map_url=map_path)


if __name__ == "__main__":
    app.run(debug=True)