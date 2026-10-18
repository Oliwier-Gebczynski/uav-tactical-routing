#pragma once

#include <vector>
#include <nlohmann/json.hpp>
#include "../common/Cell.h"

class Map{
    private:
        int width;
        int height;

        std::vector<Cell> cells;
        nlohmann::json metadata = nlohmann::json::object();

        int index(int x, int y) const;

    public:
        Map(int width, int height);

        int getWidth() const;
        int getHeight() const;

        Cell& getCell(int x, int y);
        const Cell& getCell(int x, int y) const;

        bool isInside(int x, int y) const;
        const nlohmann::json& getMetadata() const { return metadata; }
        void setMetadata(const nlohmann::json& value) { metadata = value; }
};
