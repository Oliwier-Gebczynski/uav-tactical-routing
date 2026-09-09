#include "SimulatedAnnealing.h"
#include <cmath>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <algorithm>

std::string SAResult::toString() const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2);
    oss << "=== [WYNIKI OPTYMALIZACJI SIMULATED ANNEALING + LOCAL SEARCH] ===\n";
    oss << "  Koszt początkowy E_0:    " << initialCost.totalCost
        << " (Dystans: " << initialCost.distance << "m, Zagrożenie: " << initialCost.threatRisk << ")\n";
    oss << "  Koszt końcowy E_opt:     " << bestCost.totalCost
        << " (Dystans: " << bestCost.distance << "m, Zagrożenie: " << bestCost.threatRisk << ")\n";

    float improvement = 0.0f;
    if (initialCost.totalCost > 0.001f) {
        improvement = (initialCost.totalCost - bestCost.totalCost) / initialCost.totalCost * 100.0f;
    }
    oss << "  Poprawa funkcji celu:    " << improvement << "%\n";
    oss << "  Status wykonalności:     " << (bestCost.isFeasible ? "WYKONALNA (BEZPIECZNA)" : "NIEWYKONALNA (KOLIZJE)") << "\n";
    oss << "  Liczba punktów trasy:    " << bestWaypoints.size() << " punktów kontrolnych (" << bestCost.totalPoints << " komórek siatki)\n";
    oss << "  Statystyki SA:\n";
    oss << "    - Łączna liczba prób:  " << totalIterations << "\n";
    oss << "    - Zaakceptowane ruchy (lepsze ΔE < 0): " << acceptedBetterMoves << "\n";
    oss << "    - Zaakceptowane przeskoki (gorsze exp(-ΔE/T)): " << acceptedWorseMoves << " (eksploracja globalna)\n";
    oss << "    - Odrzucone mutacje:   " << rejectedMoves << "\n";

    if (!decisionLog.empty()) {
        oss << "\n  --- [DZIENNIK KLUCZOWYCH DECYZJI TAKTYCZNYCH PLANERA (" << decisionLog.size() << " ZDARZEŃ)] ---\n";
        for (const auto& ev : decisionLog) {
            oss << "  • [Krok " << std::setw(4) << ev.iteration
                << " | T=" << std::setw(5) << std::setprecision(1) << ev.temperature << "] "
                << "[" << ev.phase << "] " << ev.details << "\n";
        }
    }
    oss << "==================================================================";
    return oss.str();
}

SimulatedAnnealing::SimulatedAnnealing(CostEvaluator evaluator, SAParameters params)
    : evaluator(evaluator), params(params) {}

std::vector<Waypoint> SimulatedAnnealing::perturbWaypoint(const std::vector<Waypoint>& current,
                                                         const Map& map,
                                                         float currentTemp,
                                                         std::mt19937& rng,
                                                         std::string* actionType,
                                                         std::string* actionDetail) const {

    std::vector<size_t> transitIndices;
    for (size_t i = 1; i < current.size() - 1; ++i) {
        if (current[i].type == WaypointType::Transit) {
            transitIndices.push_back(i);
        }
    }

    if (transitIndices.empty()) {
        return insertWaypoint(current, map, rng, actionType, actionDetail);
    }

    std::vector<Waypoint> mutated = current;
    std::uniform_int_distribution<size_t> idxDist(0, transitIndices.size() - 1);
    size_t targetIdx = transitIndices[idxDist(rng)];

    float tempFactor = std::clamp(currentTemp / params.initialTemperature, 0.15f, 1.0f);
    float currentRadius = params.maxPerturbation * std::pow(tempFactor, 0.4f);

    std::uniform_real_distribution<float> offsetDist(-currentRadius, currentRadius);
    float nx = mutated[targetIdx].x + offsetDist(rng);
    float ny = mutated[targetIdx].y + offsetDist(rng);

    nx = std::clamp(nx, 1.0f, static_cast<float>(map.getWidth() - 2));
    ny = std::clamp(ny, 1.0f, static_cast<float>(map.getHeight() - 2));

    if (actionType) *actionType = "PERTURB_WP";
    if (actionDetail) {
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(1);
        oss << "Przesunięto punkt tranzytowy CP" << mutated[targetIdx].id
            << " z (" << current[targetIdx].x << ", " << current[targetIdx].y << ") na (" << nx << ", " << ny << ")";
        *actionDetail = oss.str();
    }

    mutated[targetIdx].x = nx;
    mutated[targetIdx].y = ny;

    return mutated;
}

std::vector<Waypoint> SimulatedAnnealing::insertWaypoint(const std::vector<Waypoint>& current,
                                                        const Map& map,
                                                        std::mt19937& rng,
                                                        std::string* actionType,
                                                        std::string* actionDetail) const {
    if (current.size() >= static_cast<size_t>(params.maxWaypoints) || current.size() < 2) {
        return perturbWaypoint(current, map, params.minTemperature, rng, actionType, actionDetail);
    }

    std::uniform_int_distribution<size_t> segDist(0, current.size() - 2);
    size_t segIdx = segDist(rng);

    const auto& p1 = current[segIdx];
    const auto& p2 = current[segIdx + 1];

    float midX = 0.5f * (p1.x + p2.x);
    float midY = 0.5f * (p1.y + p2.y);
    float alt = 0.5f * (p1.altitudeAGL + p2.altitudeAGL);

    std::uniform_real_distribution<float> offsetDist(-params.maxPerturbation, params.maxPerturbation);
    float nx = std::clamp(midX + offsetDist(rng), 1.0f, static_cast<float>(map.getWidth() - 2));
    float ny = std::clamp(midY + offsetDist(rng), 1.0f, static_cast<float>(map.getHeight() - 2));

    int newId = static_cast<int>(current.size()) + 100;
    Waypoint newWp(newId, nx, ny, alt, WaypointType::Transit, "Transit");

    if (actionType) *actionType = "INSERT_WP";
    if (actionDetail) {
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(1);
        oss << "Wstawiono punkt tranzytowy CP" << newId << " (" << nx << ", " << ny << ") na odcinku " << segIdx << "-" << (segIdx + 1);
        *actionDetail = oss.str();
    }

    std::vector<Waypoint> mutated = current;
    mutated.insert(mutated.begin() + segIdx + 1, newWp);

    return mutated;
}

std::vector<Waypoint> SimulatedAnnealing::deleteWaypoint(const std::vector<Waypoint>& current,
                                                        const Map& map,
                                                        std::mt19937& rng,
                                                        std::string* actionType,
                                                        std::string* actionDetail) const {
    std::vector<size_t> transitIndices;
    for (size_t i = 1; i < current.size() - 1; ++i) {
        if (current[i].type == WaypointType::Transit) {
            transitIndices.push_back(i);
        }
    }

    if (transitIndices.empty() || current.size() <= 2) {
        return perturbWaypoint(current, map, params.minTemperature, rng, actionType, actionDetail);
    }

    std::uniform_int_distribution<size_t> idxDist(0, transitIndices.size() - 1);
    size_t delIdx = transitIndices[idxDist(rng)];

    if (actionType) *actionType = "DELETE_WP";
    if (actionDetail) {
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(1);
        oss << "Usunięto zbędny punkt tranzytowy CP" << current[delIdx].id << " (" << current[delIdx].x << ", " << current[delIdx].y << ")";
        *actionDetail = oss.str();
    }

    std::vector<Waypoint> mutated = current;
    mutated.erase(mutated.begin() + delIdx);

    return mutated;
}

std::vector<Waypoint> SimulatedAnnealing::mutate(const std::vector<Waypoint>& current,
                                                const Map& map,
                                                float currentTemp,
                                                std::mt19937& rng,
                                                std::string* actionType,
                                                std::string* actionDetail) const {
    std::uniform_real_distribution<float> roll(0.0f, 1.0f);
    float r = roll(rng);

    if (r < params.probPerturb) {
        return perturbWaypoint(current, map, currentTemp, rng, actionType, actionDetail);
    } else if (r < params.probPerturb + params.probInsert) {
        return insertWaypoint(current, map, rng, actionType, actionDetail);
    } else {
        return deleteWaypoint(current, map, rng, actionType, actionDetail);
    }
}

SAResult SimulatedAnnealing::optimize(const Mission& mission, const Map& map, unsigned int seed) {
    return optimize(mission.getAllWaypoints(), map, seed);
}

SAResult SimulatedAnnealing::optimize(const std::vector<Waypoint>& initialWaypoints, const Map& map, unsigned int seed) {
    SAResult result;
    if (initialWaypoints.size() < 2) {
        return result;
    }

    std::mt19937 rng(seed);

    Path directBaselinePath = LocalSearch::buildDensePath(initialWaypoints, map);
    CostBreakdown directBaselineCost = evaluator.evaluate(directBaselinePath, map);

    float directDist = 0.0f;
    for (size_t i = 1; i < initialWaypoints.size(); ++i) {
        float dx = initialWaypoints[i].x - initialWaypoints[i - 1].x;
        float dy = initialWaypoints[i].y - initialWaypoints[i - 1].y;
        float dz = initialWaypoints[i].altitudeAGL - initialWaypoints[i - 1].altitudeAGL;
        directDist += std::sqrt(dx * dx + dy * dy + dz * dz);
    }
    if (directDist <= 0.001f) directDist = directBaselineCost.distance;

    result.baseline.name = "Brak wyznaczania trasy (Prosta)";
    result.baseline.key = "baseline";
    result.baseline.waypoints = initialWaypoints;
    result.baseline.path = directBaselinePath;
    result.baseline.cost = directBaselineCost;
    result.baseline.stats = directBaselinePath.getStats(map);
    result.baseline.waypointsCount = static_cast<int>(initialWaypoints.size());
    result.baseline.tortuosity = 1.0f;
    result.baseline.flightTimeSec = directBaselineCost.distance / 16.667f;

    std::vector<Waypoint> lsInitWaypoints;
    for (size_t i = 0; i < initialWaypoints.size(); ++i) {
        lsInitWaypoints.push_back(initialWaypoints[i]);
        if (i + 1 < initialWaypoints.size()) {
            const auto& p1 = initialWaypoints[i];
            const auto& p2 = initialWaypoints[i + 1];
            Waypoint mid(static_cast<int>(1000 + i),
                         0.5f * (p1.x + p2.x), 0.5f * (p1.y + p2.y),
                         0.5f * (p1.altitudeAGL + p2.altitudeAGL),
                         WaypointType::Transit, "Transit_LS");
            lsInitWaypoints.push_back(mid);
        }
    }
    std::vector<Waypoint> pureLsWps = LocalSearch::optimize(lsInitWaypoints, map, evaluator);
    Path pureLsPath = LocalSearch::buildDensePath(pureLsWps, map);
    CostBreakdown pureLsCost = evaluator.evaluate(pureLsPath, map);

    result.pureLocalSearch.name = "Local Search (Tylko lokalny)";
    result.pureLocalSearch.key = "pure_ls";
    result.pureLocalSearch.waypoints = pureLsWps;
    result.pureLocalSearch.path = pureLsPath;
    result.pureLocalSearch.cost = pureLsCost;
    result.pureLocalSearch.stats = pureLsPath.getStats(map);
    result.pureLocalSearch.waypointsCount = static_cast<int>(pureLsWps.size());
    result.pureLocalSearch.tortuosity = directDist > 0.001f ? (pureLsCost.distance / directDist) : 1.0f;
    result.pureLocalSearch.flightTimeSec = pureLsCost.distance / 16.667f;

    std::vector<Waypoint> currentWaypoints = initialWaypoints;

    if (currentWaypoints.size() == 2) {
        currentWaypoints = insertWaypoint(currentWaypoints, map, rng);
    }

    Path currentPath = LocalSearch::buildDensePath(currentWaypoints, map);
    CostBreakdown currentCost = evaluator.evaluate(currentPath, map);

    result.initialCost = directBaselineCost;

    {
        DecisionEvent initEv;
        initEv.iteration = 0;
        initEv.temperature = params.initialTemperature;
        initEv.phase = "INITIAL";
        initEv.action = "DIRECT_BASELINE";
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(1);
        oss << "Wyznaczono wstępną prostą trasę bazową (Dystans: "
            << directBaselineCost.distance << "m, Ryzyko OPL: " << directBaselineCost.threatRisk
            << ", Koszt E_0: " << directBaselineCost.totalCost << ")";
        initEv.details = oss.str();
        initEv.costBefore = directBaselineCost.totalCost;
        initEv.costAfter = directBaselineCost.totalCost;
        initEv.deltaCost = 0.0f;
        result.decisionLog.push_back(initEv);
    }

    std::vector<Waypoint> bestWaypoints = currentWaypoints;
    Path bestPath = currentPath;
    CostBreakdown bestCost = currentCost;

    float temperature = params.initialTemperature;
    std::uniform_real_distribution<float> probDist(0.0f, 1.0f);

    int tempStep = 0;

    while (temperature > params.minTemperature) {
        for (int i = 0; i < params.iterationsPerTemp; ++i) {
            result.totalIterations++;

            std::string actType;
            std::string actDetail;
            std::vector<Waypoint> candidateWaypoints = mutate(currentWaypoints, map, temperature, rng, &actType, &actDetail);
            Path candidatePath = LocalSearch::buildDensePath(candidateWaypoints, map);
            CostBreakdown candidateCost = evaluator.evaluate(candidatePath, map);

            float deltaE = candidateCost.totalCost - currentCost.totalCost;

            if (deltaE < 0.0f) {

                currentWaypoints = candidateWaypoints;
                currentCost = candidateCost;
                result.acceptedBetterMoves++;

                if (currentCost.totalCost < bestCost.totalCost) {
                    float globalDelta = candidateCost.totalCost - bestCost.totalCost;

                    if (globalDelta < -1.0f || candidateCost.threatRisk < bestCost.threatRisk - 0.01f || bestWaypoints.size() != candidateWaypoints.size()) {
                        DecisionEvent ev;
                        ev.iteration = result.totalIterations;
                        ev.temperature = temperature;
                        ev.phase = "BREAKTHROUGH";
                        ev.action = actType;
                        std::ostringstream oss;
                        oss << std::fixed << std::setprecision(1);
                        oss << actDetail << " -> Nowe optimum globalne E: " << bestCost.totalCost
                            << " -> " << candidateCost.totalCost << " (ΔE: " << globalDelta
                            << ", OPL: " << candidateCost.threatRisk << ", Dystans: " << candidateCost.distance << "m)";
                        ev.details = oss.str();
                        ev.costBefore = bestCost.totalCost;
                        ev.costAfter = candidateCost.totalCost;
                        ev.deltaCost = globalDelta;
                        result.decisionLog.push_back(ev);
                    }

                    bestCost = currentCost;
                    bestWaypoints = currentWaypoints;
                    bestPath = candidatePath;
                }
            } else {

                float acceptanceProbability = std::exp(-deltaE / temperature);
                if (probDist(rng) < acceptanceProbability) {

                    if (acceptanceProbability > 0.08f && deltaE > 6.0f && (result.acceptedWorseMoves % 12 == 0)) {
                        DecisionEvent ev;
                        ev.iteration = result.totalIterations;
                        ev.temperature = temperature;
                        ev.phase = "METROPOLIS_JUMP";
                        ev.action = actType;
                        std::ostringstream oss;
                        oss << std::fixed << std::setprecision(1);
                        oss << actDetail << " -> Eksploracja bariery OPL (P="
                            << (acceptanceProbability * 100.0f) << "%, T=" << temperature << ", ΔE=+" << deltaE << ")";
                        ev.details = oss.str();
                        ev.costBefore = currentCost.totalCost;
                        ev.costAfter = candidateCost.totalCost;
                        ev.deltaCost = deltaE;
                        result.decisionLog.push_back(ev);
                    }

                    currentWaypoints = candidateWaypoints;
                    currentCost = candidateCost;
                    result.acceptedWorseMoves++;
                } else {
                    result.rejectedMoves++;
                }
            }
        }

        if (params.enablePeriodicLocalSearch && (tempStep > 0) && (tempStep % params.localSearchInterval == 0)) {
            std::vector<Waypoint> refined = LocalSearch::optimize(bestWaypoints, map, evaluator);
            Path refinedPath = LocalSearch::buildDensePath(refined, map);
            CostBreakdown refinedCost = evaluator.evaluate(refinedPath, map);

            if (refinedCost.totalCost < bestCost.totalCost) {
                float lsDelta = refinedCost.totalCost - bestCost.totalCost;
                DecisionEvent ev;
                ev.iteration = result.totalIterations;
                ev.temperature = temperature;
                ev.phase = "LOCAL_SEARCH";
                ev.action = "PERIODIC_REFINEMENT";
                std::ostringstream oss;
                oss << std::fixed << std::setprecision(1);
                oss << "Okresowy Local Search zredukował koszt z " << bestCost.totalCost
                    << " do " << refinedCost.totalCost << " (ΔE: " << lsDelta << ")";
                ev.details = oss.str();
                ev.costBefore = bestCost.totalCost;
                ev.costAfter = refinedCost.totalCost;
                ev.deltaCost = lsDelta;
                result.decisionLog.push_back(ev);

                bestWaypoints = refined;
                bestPath = refinedPath;
                bestCost = refinedCost;
                currentWaypoints = refined;
                currentCost = refinedCost;
            }
        }

        result.convergenceHistory.push_back(bestCost.totalCost);
        temperature *= params.coolingRate;
        tempStep++;
    }

    result.pureSA.name = "Simulated Annealing (Czysty SA)";
    result.pureSA.key = "pure_sa";
    result.pureSA.waypoints = bestWaypoints;
    result.pureSA.path = bestPath;
    result.pureSA.cost = bestCost;
    result.pureSA.stats = bestPath.getStats(map);
    result.pureSA.waypointsCount = static_cast<int>(bestWaypoints.size());
    result.pureSA.tortuosity = directDist > 0.001f ? (bestCost.distance / directDist) : 1.0f;
    result.pureSA.flightTimeSec = bestCost.distance / 16.667f;

    if (params.enableLocalSearch) {
        float beforeLSCost = bestCost.totalCost;
        size_t countBefore = bestWaypoints.size();

        std::vector<Waypoint> refined = LocalSearch::optimize(bestWaypoints, map, evaluator);
        Path refinedPath = LocalSearch::buildDensePath(refined, map);
        CostBreakdown refinedCost = evaluator.evaluate(refinedPath, map);

        if (refinedCost.totalCost <= bestCost.totalCost) {
            float lsDelta = refinedCost.totalCost - beforeLSCost;
            DecisionEvent ev;
            ev.iteration = result.totalIterations;
            ev.temperature = 0.0f;
            ev.phase = "LOCAL_SEARCH";
            ev.action = "FINAL_SHORTCUT_SMOOTH";
            std::ostringstream oss;
            oss << std::fixed << std::setprecision(1);
            oss << "Końcowy Local Search: zredukowano liczbę punktów z " << countBefore
                << " do " << refined.size() << ", usunięto zbędne zygzaki (E: "
                << beforeLSCost << " -> " << refinedCost.totalCost << ", Dystans: " << refinedCost.distance << "m)";
            ev.details = oss.str();
            ev.costBefore = beforeLSCost;
            ev.costAfter = refinedCost.totalCost;
            ev.deltaCost = lsDelta;
            result.decisionLog.push_back(ev);

            bestWaypoints = refined;
            bestPath = refinedPath;
            bestCost = refinedCost;
        }
    }

    result.bestWaypoints = bestWaypoints;
    result.bestPath = bestPath;
    result.bestCost = bestCost;

    result.hybridSaLs.name = "SA + Local Search (Hybryda)";
    result.hybridSaLs.key = "sa_ls";
    result.hybridSaLs.waypoints = bestWaypoints;
    result.hybridSaLs.path = bestPath;
    result.hybridSaLs.cost = bestCost;
    result.hybridSaLs.stats = bestPath.getStats(map);
    result.hybridSaLs.waypointsCount = static_cast<int>(bestWaypoints.size());
    result.hybridSaLs.tortuosity = directDist > 0.001f ? (bestCost.distance / directDist) : 1.0f;
    result.hybridSaLs.flightTimeSec = bestCost.distance / 16.667f;

    return result;
}

const SAParameters& SimulatedAnnealing::getParameters() const {
    return params;
}

void SimulatedAnnealing::setParameters(const SAParameters& newParams) {
    params = newParams;
}

const CostEvaluator& SimulatedAnnealing::getCostEvaluator() const {
    return evaluator;
}

void SimulatedAnnealing::setCostEvaluator(const CostEvaluator& newEvaluator) {
    evaluator = newEvaluator;
}
