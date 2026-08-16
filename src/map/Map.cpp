#include "Map.h"

Map::Map(int width, int height) : width(width), height(height), cells(width * height){}

int Map::getWidth() const{
    return width;
}

int Map::getHeight() const{
    return height;
}

int Map::index(int x, int y) const{
    return y * width + x;
}

bool Map::isInside(int x, int y) const{
    return x>= 0 && y >= 0 && x < width && y < height;
}

Cell& Map::getCell(int x, int y){
    return cells[index(x, y)];
}

const Cell& Map::getCell(int x, int y) const{
    return cells[index(x, y)];
}