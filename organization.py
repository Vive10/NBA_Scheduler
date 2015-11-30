# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 11:12:08 2015
Classes for teams, divisions, conferences
to provide general structure within CSP

@author: charlesliu
"""
import numpy as np

class OrgEq(object):
    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __repr__(self):
        return self.name

#Eventually want Team class to interact with domain objects to generate schedule
class Team(OrgEq):
    def __init__(self, state, name, division, indices):
        #division team is in
        self.division = division
        #name of team, e.g. Knicks
        self.name = name
        #state team is in, e.g. New York
        self.state = state
        #50-60 available dates to host home games, want an even distribution over season
        #every 5 dates pick 2 possible home dates
        self.home_dates = []
        skip = 5
        for i in range(len(indices))[::skip]:
            slice_len = len(indices[i:i+skip])
            num_pick = 2 if slice_len == skip else 1
            dates = np.random.choice(indices[i:i+5], num_pick, replace=False)
            dates.sort()
            self.home_dates += list(dates)
        #these are the conference opponents that you'll play 4 games against (6 of them)
        self.conf_opponents = set([])

class Division(OrgEq):
    def __init__(self, name, conference, teams = []):
        #name of division
        self.name = name
        #conference division is in
        self.conference = conference
        #teams in division
        self.teams = dict(zip(map(lambda x: x.name, teams), teams))
        
class Conference(OrgEq):
    def __init__(self, name, divisions = []):
        self.name = name
        #divisions in conference
        self.divisions = dict(zip(map(lambda x: x.name, divisions), divisions))    
    
    def get_team(self, name):
        for division in self.divisions.values():
            if name in division.teams:
                return division.teams[name]
        return None
        
    def teams(self):
        teams = []
        for division in self.divisions.values():
            teams += division.teams.values()
        return teams
        
class League(OrgEq):
    def __init__(self, conferences = []):
        self.conferences = dict(zip(map(lambda x: x.name, conferences), conferences))
        self.name = "NBA"

    def get_division(self, name):
        for conference in self.conferences.values():
            if name in conference.divisions:
                return conference.divisions[name]
        return None
    
    def get_team(self, name):
        for conference in self.conferences.values():
            for division in conference.divisions.values():
                if name in division.teams:
                    return division.teams[name]
        return None
    
    def teams(self):
        teams = []
        for conference in self.conferences.values():
            teams += conference.teams()
        return teams
        
        


