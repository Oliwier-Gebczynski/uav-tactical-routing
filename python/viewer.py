import json
import numpy as np
import matplotlib.pyplot as plt
import os

TERRAIN_COLORS = {
    "grass": 0,
    "field": 1,
    "forest": 2,
    "road": 3,
    "building": 4,
    "water": 5
}

def load_map(filename):
    with open(filename, "r") as file:
        data = json.load(file)
    return data


def convert_to_matrix(map_data):
    height = map_data["height"]
    width = map_data["width"]

    matrix = np.zeros((height, width))

    for y in range(height):
        for x in range(width):
            terrain = map_data["cells"][y][x]["terrain"]
            matrix[y][x] = TERRAIN_COLORS.get(terrain, 0)

    return matrix

def display_map(matrix):
    colors = [
        "lightgreen",
        "yellow",
        "darkgreen",
        "gray",
        "black",
        "blue"
    ]

    cmap = plt.cm.colors.ListedColormap(colors)
    plt.figure(figsize=(10,10))
    plt.imshow(
        matrix,
        cmap=cmap,
        interpolation="nearest"
    )
    plt.title("UAV Terrain Map")
    plt.axis("off")
    plt.show()



def save_image(matrix, filename):
    colors = [
        "lightgreen",
        "yellow",
        "darkgreen",
        "gray",
        "black",
        "blue"
    ]

    cmap = plt.cm.colors.ListedColormap(colors)
    plt.figure(figsize=(10,10))
    plt.imshow(
        matrix,
        cmap=cmap,
        interpolation="nearest"
    )
    plt.axis("off")
    plt.savefig(
        filename,
        bbox_inches="tight",
        dpi=300
    )
    plt.close()



if __name__ == "__main__":

    json_file = "../data/maps/test_map.json"
    map_data = load_map(json_file)
    matrix = convert_to_matrix(map_data)
    display_map(matrix)
    save_image(
        matrix,
        "../data/maps/test_map.png"
    )


    print("Map visualization finished")