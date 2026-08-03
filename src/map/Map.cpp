#include "Map.h"

Map::Map(int width, int height){
    this->width = width;
    this->height = height;

    cells.resize(height);

    for(auto& row : cells){
        row.resize(width);
    }
}

int Map::getWidth() const{
    return width;
}

int Map::getHeight() const{
    return height;
}

Cell& Map::getCell(int x, int y){
    return cells[y][x];
}

const Cell& Map::getCell(int x, int y) const{
    return cells[y][x];
}