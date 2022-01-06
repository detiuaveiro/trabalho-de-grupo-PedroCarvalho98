import sys
from typing import Tuple


from actions import *
from utils import *
from utils import _PRINT

import json
import numpy as np
import math

DEBUG_FILE = "client_debug.txt"

def debug(*args):
    _PRINT(*args, file=sys.stderr, flush=True)
    with open(DEBUG_FILE, 'a') as f:
        stdout, sys.stdout = sys.stdout, f # Save a reference to the original standard output
        _PRINT(*args)
        sys.stdout = stdout

print = debug # dont erase this line, otherwise you cannot use the print function for debug 

def upgradeBase():
    return f"{UPGRADE_BUILDING}"

def recruitSoldiers(type, amount, location=(1,VCENTER)):
    return f"{RECRUIT_SOLDIERS}|{type}|{amount}|{location[0]}|{location[1]}".replace(" ","")

def moveSoldiers(pos, to, amount):
    return f"{MOVE_SOLDIERS}|{pos[0]}|{pos[1]}|{to[0]}|{to[1]}|{amount}".replace(" ","")

def playActions(actions):
    _PRINT(';'.join(map(str,actions)), flush=True)



# ENVIRONMENT
class Environment:
    def __init__(self, difficulty, base_cost, base_prod):
        self.difficulty = difficulty
        self.resources = 0
        self.building_level = 0
        self.base_cost = base_cost
        self.base_prod = base_prod
        self.board = [[None]*WIDTH for h in range(HEIGHT)]
        playActions([])

    @property
    def upgrade_cost(self):
        return int(self.base_cost*(1.4**self.building_level))


    @property
    def production(self):
        return int(self.base_prod*(1.2**self.building_level))


    def readEnvironment(self):
        state = input()
        
        if state in ["END", "ERROR"]:
            return state
        level, resources, board = state.split()
        level = int(level)
        resources = int(resources)
        debug(f"Building Level: {level}, Current resources: {resources}")
        self.building_level = level
        self.resources = resources
        self.board = json.loads(board)

        # uncomment next lines to use numpy array instead of array of array of array (3D array)
        # IT IS RECOMMENDED for simplicity
        # arrays to numpy converstion: self.board[y][x][idx] => self.board[x,y,idx]
        #
        self.board = np.swapaxes(np.array(json.loads(board)),0,1)
        debug(self.board.shape)

    #----------------------------------

    def verifyproximity(self, my_position):
        # --------FUNCTION-----------
        # > def verifyproximity()
        # --------DESCRIPTION--------
        # This funtion verifies the proximity of enemies in relation to the current cell.
        # If an enemy is closer than 4 cells of distance, it returns a flag to indicate that there are enemies nearby.
        # --------INPUTS-------------
        # > my_position (from a certain entity)
        # --------OUTPUTS------------
        # > flag proximity_enemies
        # ---------------------------

        enemies = np.where(self.board[:,:,0]==ENEMY_SOLDIER_MELEE)
        enemies = [(a,b) for a,b in zip(enemies[0],enemies[1])]

        #print("My Position:", my_position)

        for i in range(len(enemies)):
            enemy_position = enemies[i]
            #print("Enemy Position:", enemy_position)
            difference = (my_position[0] - enemy_position[0], my_position[1] - enemy_position[1])
            if abs(difference[0])<=4 and abs(difference[1])<=4:
                proximity_enemies = 1
            else:
                proximity_enemies = None

        return proximity_enemies

    #----------------------------------

    #--------ACTION FUNCTIONS---------- 

   
    def ActionRange(self,entities,flags):
        # --------FUNCTION-----------
        # > def ActionRange()
        # --------DESCRIPTION--------
        # This function makes the ranged move to the cell above, near the wall (height = 0).
        # If they are on the cell explained above, they only move to the right to attack the enemies.
        # --------INPUTS-------------
        # > entities, flags
        # --------OUTPUTS------------
        # > moveaction
        # ---------------------------  

        if entities[0][1]!=0: #Sobe sempre os Ranged
            here=entities[0]
            togo=(entities[0][0],entities[0][1]-1)
            soldamount=entities[1][1]
            moveaction = moveSoldiers(here,togo,soldamount)
            return moveaction
        #Mover Ranged para direita    
        if entities[0][1]==0 and\
        (self.board[entities[0][0]+1,entities[0][1],0]==ALLIED_SOLDIER_RANGED or self.board[entities[0][0]+1,entities[0][1],0]==None): #Adicionar Proximity Flag
            here=entities[0]
            togo=(entities[0][0]+1,entities[0][1])
            soldamount=math.ceil(entities[1][1]/3)
            if soldamount<=1:
                pass
            moveaction = moveSoldiers(here,togo,soldamount)
            return moveaction
        return None
    
    #---------------------------------- 

    def ActionMelee(self,entities,flags):
        # --------FUNCTION-----------
        # > def ActionMelee()
        # --------DESCRIPTION--------
        # This function makes the melee move to the cell on the bottom, near the wall (height = 0).
        # --------INPUTS-------------
        # > entities, flags
        # --------OUTPUTS------------
        # > moveaction
        # --------------------------- 

        if entities[0][1]!=10: #Descer Sempre os Melee
            here=entities[0]
            togo=(entities[0][0],entities[0][1]+1)
            soldamount=entities[1][1]
            moveaction = moveSoldiers(here,togo,soldamount)
            return moveaction
        return None

    #----------------------------------

    def play(self): # agent move, call playActions only ONCE
        # --------FUNCTION-----------
        # > def play()
        # --------DESCRIPTION--------
        # Makes the agent move.
        # --------INPUTS-------------
        # > None
        # --------OUTPUTS------------
        # > None
        # --------------------------- 

        #----------------------------------
        # TO-DO FLAGS
        flags=dict()
        # flag to verify if the cell to go is empty (first - empty, second - type)
        available_cell = [None,None]
        
        # flag to verify if there are sufficient resources to buy base upgrade
        resources_qntbase = 0
        
        # flag to verify if there are sufficient resources to buy x melees
        resources_qntmelees = 0
        
        # flag to verify if there are sufficient resources to buy x ranges
        resources_qntranges = 0
        
        # flag to verify the progress of the game (early game, mid game, late game)
        game_progress = None

        # flag to verify the proximity of enemies for ranges and other for melees (first - ranges, second - melees)    
        proximity_enemies= None
        
        # flag for retard (20000 max)
        retard = 0

        #----------------------------------
        # INITIALIZATION

        actions = []
        print("Current production per turn is:", self.production)
        print("Current building cost is:", self.upgrade_cost)
        if self.resources >= self.upgrade_cost: # upgrade building

            actions.append(upgradeBase())
            self.resources -= self.upgrade_cost

        # only buy ranged
        default_cell_s_type = self.board[1,VCENTER,0]  # in numpy would be self.board[1,VCENTER,0]
        if self.resources>=SOLDIER_MELEE_COST*(self.building_level+1) and default_cell_s_type in [EMPTY_CELL, ALLIED_SOLDIER_MELEE]:
           # buyamount = self.resources//SOLDIER_RANGED_COST
           print(str('\n')+str(self.building_level)+str("\n"))
           buyamount=self.building_level+1
           actions.append( recruitSoldiers(ALLIED_SOLDIER_MELEE, buyamount) )
           self.resources -= buyamount*SOLDIER_MELEE_COST

        #----------------------------------
        # MAP SEARCH

        print("Entity: ")
        entities=np.where(self.board[:,:,0]!=None)
        entities=[[(a,b)] for a,b in zip(entities[0],entities[1])]
        #print(entities)
        for i in range(len(entities)):
            soldtype=self.board[entities[i][0][0],entities[i][0][1],0]
            quant=self.board[entities[i][0][0],entities[i][0][1],1]
            entities[i].append((soldtype,quant))
        print("Entity results:", entities)

        #-----------------------------------
        # ACTIONS

        for i in range(len(entities)):
            my_position = entities[i][0]
            self.verifyproximity(my_position)
            if entities[i][1][0]==ALLIED_SOLDIER_RANGED:
                moveaction=self.ActionRange(entities[i],flags)
                if moveaction == None:
                    continue
                actions.append(moveaction)
            elif entities[i][1][0]==ALLIED_SOLDIER_MELEE:
                moveaction=self.ActionMelee(entities[i],flags)
                if moveaction == None:
                    continue
                actions.append(moveaction)

        playActions(actions)

    #----------------------------------

    
def main():
    
    open(DEBUG_FILE, 'w').close()
    difficulty, base_cost, base_prod = map(int,input().split())
   
    env = Environment(difficulty, base_cost, base_prod)
    while 1:
        signal = env.readEnvironment()
        if signal=="END":
            debug("GAME OVER")
            sys.exit(0)
        elif signal=="ERROR":
            debug("ERROR")
            sys.exit(1)

        env.play()
        

if __name__ == "__main__":
    main()


