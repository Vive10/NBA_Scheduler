# -*- coding: utf-8 -*-
"""
Created on Sat Nov 21 12:24:56 2015

CSP code running DFS on variables

@author: charlesliu
"""

import domain as dom
import datagen as dg
import json
import os
import constraint
import heapq as Q

def write_output(domains, filename):
    try:
        os.remove(filename)
    except OSError:
        pass
    with open(filename + '.json', 'w') as fp:
        json.dump(map2list(domains), fp)

def read_output(league, filename):
    with open(filename + '.json', 'r') as fp:
        domains = list2map(league, json.load(fp))
    return domains

def map2list(m):
    l = []
    for k,v in m.iteritems():
        new_k = []
        new_v = v.name if type(v) is dg.org.Team else (str(v) if type(v) is dg.datetime.date else v)
        if type(k) is int:
            l.append({'key':k, 'value':new_v})
        else:
            for t in k:
                if type(t) is dg.org.Team:
                    new_k.append(t.name)
                else:
                    new_k.append(t)
            l.append({'key':new_k, 'value': new_v})
    return l

def list2map(league, l):
    m = {}
    for kv in l:
        new_v = league.get_team(kv['value']) if type(kv['value']) is unicode else kv['value']
        if new_v is None: new_v = kv['value']
        if type(kv['key']) is list:
            new_k = []
            for t in kv['key']:
                if type(t) is unicode:
                    new_k.append(league.get_team(t))
                else:
                    new_k.append(t)
            m[tuple(new_k)] = new_v
        else:
            m[kv['key']] = new_v
    return m

def binary_search(A,x,lo=0, hi=None):
    # Binary Search that returns the index of x if x is in the array A
    # otherwise, returns the index of minimum element that is larger than x
    # Returns None if there is no element greater than or equal to x
    # lo index
    # hi index
    if hi == None:
        hi = len(A)-1
    if hi - lo <= 0:
        for i in range(lo,len(A)):
            if A[i] >= x:
                return i
        return None
    mid = (hi-lo)/2 + lo
    mid_val = A[mid]
    if x == mid_val:
        return mid
    elif x < mid_val:
        return binary_search(A,x,lo,mid-1)
    else:
        # x > mid_val
        return binary_search(A,x,mid+1, hi)


def date_ranges(multiplier, team, game_num):
    dates = []
    window = 10
    for i in range(multiplier*game_num-window, multiplier*game_num+window+1):
        if i in team.home_dates:
            dates.append(i)
    return dates


class Scheduler(object):
    def __init__(self, year, matchups_json = False, venues_dates_json = False):
        self.data = dg.DataGen(year)
        self.matchups_json = matchups_json
        self.venues_dates_json = venues_dates_json
        self.debug = True

    def set_debug(self, t):
        self.debug = t

    def create_schedule(self):
        if self.debug: print "{}: Starting".format(dg.datetime.datetime.today())
        matchups = None
        initialState = dom.Matchups(None, self.data.league, self.data.game_indices)
        if self.matchups_json:
            matchups = read_output(self.data.league, "Matchups")
        else:
            matchups, matchups_statesExplored = self.DFS(initialState)
            if self.debug: print "{}: Matchups, {} states explored, {}".format(dg.datetime.datetime.today(), matchups_statesExplored, matchups is not None)

        if matchups is not None:
            write_output(matchups, "Matchups")
            #now we have our matchups which is a dict of (team, game_num) -> [opponent]
            #we next want to assign home/away so we create a map of the form:
            #(team1, team2, game_num) -> [True/False]
            #where True indicates it's played at team1's venue
            #also team1 < team2 alphabetically
            venues_dates = None
            if self.venues_dates_json:
                venues_dates = {}
                venues = read_output(self.data.league, "Venues")
                dates = read_output(self.data.league, "Dates")
                self.data.game_indices = read_output(self.data.league, "I2D")
                for state in venues:
                    venues_dates[state] = (dates[state], venues[state])
            else:
                venues_domains = {}
                venues_selected = {}
                master_dates = {}
                for state in matchups:
                    t, g_n = state
                    o = matchups[state]
                    sk = (t, o, g_n) if t.name < o.name else (o, t, g_n)
                    dk = (t, o) if t.name < o.name else (o, t)
                    if sk not in venues_selected:
                        venues_selected[sk] = None
                        dates_true = date_ranges(2, dk[0], g_n)
                        dates_false = date_ranges(2, dk[1], g_n)
                        master_dates[(sk,True)] = dates_true
                        master_dates[(sk,False)] = dates_false
                        venues_domains[dk] = [True, False] * ((dom.constraint.total_games(initialState, t, o) + 1)/2)
                venueState = dom.Venues({initialState.domains: venues_domains, initialState.selected: venues_selected,\
                                         initialState.master_dates: master_dates})
                venues_dates, venues_statesExplored = self.DIJKSTRAS(venueState)
                #venues_dates, venues_statesExplored = self.DFS(venueState)
                if self.debug: print "{}: Venues, {} states explored, {}".format(dg.datetime.datetime.today(), venues_statesExplored, venues_dates is not None)

            if venues_dates is not None:
                venues = {}
                dates = {}
                #write_output(venu, "Dates")
                #create a master map of everything of the form:
                #(team, game_num) -> (opponent, home, dateindex)
                #where home is true if played at team's venue
                sched_map = {}
                for state in venues_dates:
                    t1, t2, g_n = state
                    date, home = venues_dates[state]
                    sched_map[(t1, g_n)] = (t2, home, date)
                    sched_map[(t2, g_n)] = (t1, not home, date)
                    venues[state] = home
                    dates[state] = date
                #sanity check that everything is right
                for team in self.data.league.teams():
                    date = -20
                    opponent_venue = {}
                    for i in range(1, 83):
                        opponent, t_f, d = sched_map[(team, i)]
                        if date >= d:
                            print "invalid date. game {} has date {}, game {} has date {}".format(i-1, date, i, d)
                        date = d
                        key = (opponent, t_f)
                        constraint.add(opponent_venue, key)
                    for opponent in self.data.league.teams():
                        if opponent is not team:
                            if opponent_venue[(opponent, True)] < (constraint.total_games(initialState, team, opponent))/2:
                                print "not enough home games"
                            if opponent_venue[(opponent, False)] < (constraint.total_games(initialState, team, opponent))/2:
                                print "not enough away games"
                            if opponent_venue[(opponent, True)] + opponent_venue[(opponent, False)] != constraint.total_games(initialState, team, opponent):
                                print "not enough games"
                write_output(venues, "Venues")
                write_output(dates, "Dates")
                write_output(self.data.i2d, "I2D")
                return sched_map

        return None

    def DFS(self, initialState):
        frontier = [initialState]
        statesExplored = 0

        while frontier:
            state = frontier.pop()
            statesExplored += 1
            if statesExplored % 1000 == 0:
                num_selected = 0
                for s in state.states[state.selected]:
                    if state.states[state.selected][s] is not None:
                        num_selected += 1
                print "{}: {}, {}, {}".format(dg.datetime.datetime.today(), statesExplored, len(frontier), num_selected)

            if state.complete():
                return (state.states[state.selected], statesExplored)
            else:
                successors = state.successors()
                if successors is not None:
                    frontier.extend(successors)
        return (None, statesExplored)

    def DIJKSTRAS(self, initialState):
        '''
        Use Dijkstra's algorithm to find a schedule that satisfies
        the m games in n nights constraint.
        If "Violated m in n rule" in printed before a schedule is returned,
        then there is no valid schedule that satisfies the m games in n nights.
        The algorithm works as follow:
            1. The initial state (where no matchups have been assigned
                dates or venues), is assigned a cost of 1230 (the number of
                remaining unassigned matchups)
            2.  Note: that a successor state is the current state with one more
                matchup assigned a date and venue.
                Each successor state is assigned a cost, where the cost is
                (total number of matchups = 1230) - (number of matchups assigned)
                + abs((date of new assignment) - ((game number of new assignment)-1)*2)


                However if at least one team plays at least m games in n nights,
                 10000 is added to the cost.

                Note: abs((date of new assignment) - ((game number of new assignment)-1)*2)
                    is the distance between the assigned date, and the ideal date
                    (where the ideal date is the (game number - 1) * 2)



            3. The cost is used as the priority when adding a state to the
            frontier priority queue.

            Note: This cost function prioritizes schedules that have assign dates closer
                to the ideal date and schedules that are closer to the goal
                (i.e. more assigned games).  In addition, it gives very low priority
                to schedules that break the m games in n nights constraint,
                only exploring those schedules after exhausting all other options.
        '''
        frontier = []
        Q.heapify(frontier)

        statesExplored = 0
        # the key is a tuple assigned matchups in the schedule
        # the value is the total cost at that assignment
        state_cost = {}

        # get the key to represent the state in the dictionary
        selected_list = []
        for assignment in initialState.states[initialState.selected].items():
            if assignment[1] is not None:
                selected_list.append(assignment)
        key = tuple(selected_list)

        # Initialize
        state_cost[key] = initialState.states[initialState.current_cost]
        priority = state_cost[key]

        Q.heappush(frontier, (priority, initialState))

        while len(frontier) > 0:
            state_priority, state = Q.heappop(frontier)
            if state.states[state.current_cost] > 10000:
                print "Violated m in n rule"
            statesExplored += 1
            if statesExplored % 100 == 0:
                num_selected = 0
                for s in state.states[state.selected]:
                    if state.states[state.selected][s] is not None:
                        num_selected += 1
                print "{}: {}, {}, {}, {}".format(dg.datetime.datetime.today(), statesExplored, len(frontier), num_selected, state_priority)

            if state.complete():
                # all dates have been assigned
                return (state.states[state.selected], statesExplored)
            else:
                # Get successors
                successors = state.successors()
                if successors is not None and len(successors) != 0:
                    for successor in successors:
                        selected_list = []
                        # Get key for this successor state
                        for assignment in successor.states[state.selected].items():
                            if assignment[1] is not None:
                                selected_list.append(assignment)
                        key = tuple(selected_list)
                        cost = successor.states[successor.current_cost]

                        # Add successor state to priority queue if cost < previous cost to that state
                        if key not in state_cost or cost < state_cost[key]:
                            state_cost[key] = cost

                            priority = cost
                            Q.heappush(frontier, (priority, successor))
        return (None, statesExplored)

    #methods for printing schedules
    def str_schedule(self, schedule, games = 82, teams = []):
        output = "Date,Home,Away\n"
        if type(teams) is str:
            teams = [teams]
        for t in (teams if len(teams) > 0 else self.data.league.teams()):
            t = self.data.league.get_team(t) if type(t) is str else t
            for i in range(1, games + 1):
                dom_elem = schedule[(t, i)]
                output += self.str_game(t, dom_elem) + "\n"
        return output

    def str_game(self, team, dom_elem):
        opponent, home, dateindex = dom_elem
        return "{},{},{}".format(self.data.i2d[dateindex], team.name if home else opponent.name, opponent.name if home else team.name)

if __name__ == '__main__':
    #The 2 True's correspond to reading in Matches.json and Venues.json so you don't have to recalculate
    sched = Scheduler(2015,True,False)
    today = dg.datetime.datetime.today()
    new_sched = sched.create_schedule()
    fin = dg.datetime.datetime.today()
    elapsed = fin - today
    elapsed = elapsed.total_seconds()
    #calculates minutes to run
    print elapsed/60.
    #sched is now a map of (team, game_num) -> (opponent, home, dateindex)