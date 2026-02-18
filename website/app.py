from flask import Flask, render_template, request, url_for
import os
import folium
import webbrowser
from PIL import Image
import io
import pandas as pd
import numpy as np

# get network data
stations = pd.read_csv("../data/stations.csv")
routes = pd.read_csv("../data/routes.csv")
lineColours = pd.read_csv("../data/routeColours.csv")

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

### WEB APPLICATION ###
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", map_url="static/map.html")

@app.route("/process", methods=["POST"])
def process():
    # get input from HTML
    line = request.form["station-name-input"].upper().strip()

    # protect against harmful input
    if not line.isalnum():
        #return "Invalid Input", 400
        return render_template("index.html", error="Invalid input", map_url="static/map.html")

    # the S41 has bee excluded from the dataset because it has the same stations and routes as the S42
    allBerlinLines = list(routes.linie.unique())
    allBerlinLines.append("S41")
    if line == "S41":
        line = "S42"
    elif line == "ALL":
        return render_template("index.html", map_url="static/map.html")
    elif line not in allBerlinLines:
        #return "That is not a Berlin train line", 400
        return render_template("index.html", error="That is not a Berlin train line.", map_url="static/map.html")

    # generate new map
    m_sub = folium.Map(tiles="cartodb positron", location=(52.52, 13.40), zoom_start=10)
    subS, subR = extractTrainline(stations, routes, line)
    plotStations(m_sub, subS, subR)
    plotTrainConnections(m_sub, subS, subR)
    m_sub.save("static/map-subset.html")

    # render page with new map
    generated_map_url = url_for('static', filename='map-subset.html')
    return render_template("index.html", map_url=generated_map_url)

if __name__ == "__main__":
    app.run(debug=True)