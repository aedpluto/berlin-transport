def displayConnections(stations, route, delimiter="\n"):
    slist = stations.split(delimiter)
    output = ""
    for i in range(len(slist)-1):
        newconnection = slist[i] + "," + slist[i+1] + "," + route
        output = output + newconnection + "\n"
    return output[:-1]

def updateConnections(stations, route, filename, delimiter="\n"):
    text = displayConnections(stations, route, delimiter=delimiter)
    with open(filename, "a") as routefile:
        routefile.write(text)
    return "Success"
