#pragma once

#include <vector>
#include "../common/Cell.h"

class Map{
    private:
        int width;
        int height;

        std::vector<Cell> cells;

        int index(int x, int y) const;

    public:
        Map(int width, int height);

        int getWidth() const;
        int getHeight() const;

        Cell& getCell(int x, int y);
        const Cell& getCell(int x, int y) const;

        bool isInside(int x, int y) const;
};