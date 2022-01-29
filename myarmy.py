#-----------IMPORTS-------------
from os import sendfile
import sys
from typing import Tuple


from actions import *
from utils import *
from utils import _PRINT

import json
import numpy as np
import math
#-------------------------------

#-------GLOBAL VARIABLES--------
global flags
#-------------------------------

#------------DEBUG--------------
DEBUG_FILE = "client_debug.txt"
def debug(*args):
    _PRINT(*args, file=sys.stderr, flush=True)
    with open(DEBUG_FILE, 'a') as f:
        stdout, sys.stdout = sys.stdout, f # Save a reference to the original standard output
        _PRINT(*args)
        sys.stdout = stdout

print = debug # dont erase this line, otherwise you cannot use the print function for debug
#-------------------------------

#-----------ACTIONS-------------
def upgradeBase():
    return f"{UPGRADE_BUILDING}"

def recruitSoldiers(type, amount, location=(1,VCENTER)):
    return f"{RECRUIT_SOLDIERS}|{type}|{amount}|{location[0]}|{location[1]}".replace(" ","")

def moveSoldiers(pos, to, amount):
    return f"{MOVE_SOLDIERS}|{pos[0]}|{pos[1]}|{to[0]}|{to[1]}|{amount}".replace(" ","")

def playActions(actions):
    _PRINT(';'.join(map(str,actions)), flush=True)
#-------------------------------

#-------------------------------
# ENVIRONMENT
class Environment:
    def __init__(self, difficulty, base_cost, base_prod):
        self.difficulty = difficulty
        self.resources = 0
        self.building_level = 0
        self.base_cost = base_cost
        self.base_prod = base_prod
        self.board = [[None]*WIDTH for h in range(HEIGHT)]
        self.turn = 1
        self.retard_now = 0
        self.retard_needed = 0
        self.enemies_next5rounds = []
        self.retard_max = 0
        self.watchrounds = 5
        self.spawn_soldiers = 2 
        playActions([])

    def rounds_to_wait(self):
        return self.upgrade_cost/(self.production*0.2)

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

    #---------------------------------

    #--------FLAGS FUNCTIONS----------

    def verifyproximity(self, my_position, flags):
        # --------FUNCTION-----------
        # > def verifyproximity()
        # --------DESCRIPTION--------
        # This funtion verifies the proximity of enemies in relation to the current cell.
        # If an enemy is closer than 4 cells of distance, it returns a flag to indicate that there are enemies nearby.
        # --------INPUTS-------------
        # > my_position (from a certain entity)
        # > flags (dictionary of the available flags)
        # --------OUTPUTS------------
        # > flags
        # ---------------------------

        enemies = np.where(self.board[:,:,0]==ENEMY_SOLDIER_MELEE)
        enemies = [(a,b) for a,b in zip(enemies[0],enemies[1])]

        #print("My Position:", my_position)

        for i in range(len(enemies)):
            enemy_position = enemies[i]
            #print("Enemy Position:", enemy_position)
            difference = (my_position[0] - enemy_position[0], my_position[1] - enemy_position[1])
            if abs(difference[0])<=4 and abs(difference[1])<=4:
                flags.update({"proximity_enemies":1})
                print("Enemy Detected")
            else:
                flags.update({"proximity_enemies":None})


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
        attack_radius=[]   
        for i in range (-3,4):
            for n in range (-3,4):
                if abs(n)+abs(i)==3:
                    attack_radius.append((n,i))
                    
        enemies=[]
        for attack in attack_radius:
            attack_x,attack_y=attack
            coord_x,coord_y=entities[0][0]+attack_x, entities[0][1]+attack_y
            if not (0<=coord_x<WIDTH and 0<=coord_y<HEIGHT):
                continue
            target=self.board[coord_x,coord_y]
            if target[0]==ENEMY_SOLDIER_MELEE:   
                enemies.append(target[1])
        print(enemies)

        if entities[0]== (1,VCENTER) or entities[0]==(1,VCENTER-1) or entities[0]== (0,VCENTER-1) :
            return None
        else:
            if entities[0][1]!=0: #Caso não esteja no topo da board
                here=entities[0]
                togo=(entities[0][0],entities[0][1]-1)
                soldamount=entities[1][1]
                sendamount=soldamount
                if enemies!=[]:
                    sendamount=min(sendamount,soldamount-max(enemies))
                    if self.board[togo[0],togo[1],0]==ENEMY_SOLDIER_MELEE:          
                        return None
                if sendamount<=0:
                    return None
                moveaction = moveSoldiers(here,togo,sendamount)
                return moveaction
            #Mover Ranged para direita
            if entities[0][1]==0 and self.turn>10:
                here=entities[0]
                togo=(entities[0][0]+1,entities[0][1])
                soldamount=entities[1][1]
                if (here[0]+3<WIDTH and self.board[here[0]+3,here[1],0]==ALLIED_SOLDIER_RANGED): #Caso seja da parte de trás do grupo
                    sendamount=soldamount
                else: #Seja da frente ou meio
                    if soldamount<7:
                        return None
                    sendamount=math.ceil(soldamount/2)
                if enemies!=[]:
                    sendamount=min(sendamount,soldamount-max(enemies))
                if self.board[togo[0],togo[1],0]==ENEMY_SOLDIER_MELEE:          
                    return None
                if sendamount<=0:
                    return None
                moveaction = moveSoldiers(here,togo,sendamount)
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
            if self.turn < 1 or self.turn>8:
                return moveaction
        if entities[0][1]==10:
            here=entities[0]
            togo=(entities[0][0]+1,entities[0][1])
            soldamount=entities[1][1]
            sendamount=20
            if soldamount<1:
                return None
            if soldamount<20:
                sendamount=soldamount
            moveaction = moveSoldiers(here,togo,sendamount)
            if self.turn < 1 or self.turn>8:
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
        #----------------------------

        #----------------------------
        # INITIALIZATION

        #-----------FLAGS------------

        flags = {
            "available_cell" : [None,None], # flag to verify if the cell to go is empty (first - empty, second - type)
            "bought_qntmelees" : 0, # flag to verify the quantity that was bought of melees
            "bought_qntranges" : 0, # flag to verify the quantity that was bought of ranged
            "game_progress" : None, # flag to verify the progress of the game (early game, mid game, late game)
            "proximity_enemies" : None, # flag to verify the proximity of enemies for ranges and other for melees (first - ranges, second - melees)
            "retard" : 0 # flag for retard (20000 max)
        }

        
        #-----------------------------

        #-------INFORMATIONS----------

        actions = []
        print("Current production per turn is:", self.production)
        print("Current building cost is:", self.upgrade_cost)
        print(f"Need to survive {self.rounds_to_wait()} rounds to be profitable to upgrade the base!")

        #-----------------------------
        
        #-------Calculations----------
        last_collum = self.board[WIDTH-1,:]
        for a in last_collum:
            if a[0] == ALLIED_SOLDIER_RANGED or a[0] == ALLIED_SOLDIER_MELEE:
                self.retard_now += a[1]/5.0 # Quantity
        self.spawn_soldiers = 2 + int((max(self.turn - self.retard_now, self.turn/3)**2)/65)
        self.retard_max = (2/3) * self.turn
        self.retard_needed = self.retard_max - self.retard_now
        for k in range(self.watchrounds):
            self.enemies_next5rounds.append(2 + int((max(self.turn+k - self.retard_now, (self.turn+k)/3)**2)/65))

        print("Current retard: ", self.retard_now)
        print("Current enemies spawning: ", self.spawn_soldiers)
        print("Max retard: ", self.retard_max)
        print("Retard Needed: ", self.retard_needed)
        print("Number of spawn enemies spawning in the next 5 rounds: ", self.enemies_next5rounds)


        #-----------------------------

        #----------ECONOMY------------

        #---------EARLY GAME----------
        # Untill base level <= 7 upgrade base if possible
        if self.building_level <= 6  or self.resources >= 3*self.upgrade_cost:
            if self.resources >= self.upgrade_cost:     # flag
                actions.append(upgradeBase())
                self.resources -= self.upgrade_cost
        #-----------------------------

        #----------MID GAME-----------
        # front_base_type = self.board[1,VCENTER,0]
        # front_base_quant = self.board[1,VCENTER,1]
        # if self.building_level > 6 and front_base_type in [EMPTY_CELL, ALLIED_SOLDIER_RANGED] and self.resources>=SOLDIER_RANGED_COST and front_base_quant <= 0:
        #     ranges_amount = (self.resources//SOLDIER_RANGED_COST)
        #     actions.append(recruitSoldiers(ALLIED_SOLDIER_RANGED, ranges_amount))
        #     self.resources -= ranges_amount * SOLDIER_RANGED_COST
            #melees_amount = (self.resources//SOLDIER_MELEE_COST)
            #if melees_amount > 8:
            #    melees_amount == 8
            #actions.append(recruitSoldiers(ALLIED_SOLDIER_MELEE, melees_amount, (0, VCENTER+1)))
            #self.resources -= melees_amount * SOLDIER_MELEE_COST 

        front_base_type = self.board[1,VCENTER,0]
        front_base_quant = self.board[1,VCENTER,1]
        # Buy enough ranges to kill my enemies from 5 rounds in the future
        if self.building_level > 6 and self.spawn_soldiers < 850 and front_base_type in [EMPTY_CELL, ALLIED_SOLDIER_RANGED] and self.resources>=SOLDIER_RANGED_COST:
            ranges_amount= math.ceil(self.enemies_next5rounds[4]*2/3)
            if ranges_amount > (self.resources//SOLDIER_RANGED_COST):
                actions.append(recruitSoldiers(ALLIED_SOLDIER_RANGED, (self.resources//SOLDIER_RANGED_COST)))
                self.resources-= (self.resources//SOLDIER_RANGED_COST) * SOLDIER_RANGED_COST
            else:
                actions.append(recruitSoldiers(ALLIED_SOLDIER_RANGED, ranges_amount))
                self.resources -= ranges_amount * SOLDIER_RANGED_COST
            
            # Always buy Melees (max = 20 -> to be invisible)
            melees_amount=max(self.turn//100 + 8, 20)
            if melees_amount*SOLDIER_MELEE_COST > self.resources:
                actions.append(recruitSoldiers(ALLIED_SOLDIER_MELEE, melees_amount,(0, VCENTER+1)))
                self.resources -= melees_amount * SOLDIER_MELEE_COST
            elif self.resources>SOLDIER_MELEE_COST:
                actions.append(recruitSoldiers(ALLIED_SOLDIER_MELEE, (self.resources//SOLDIER_MELEE_COST),(0, VCENTER+1)))
                self.resources-= (self.resources//SOLDIER_MELEE_COST) * SOLDIER_MELEE_COST

            # See if we have resources for anything
            nr_of_melee=self.resources//SOLDIER_MELEE_COST
            nr_of_ranged=self.resources//SOLDIER_RANGED_COST
            nr_of_upgrade=self.resources//self.upgrade_cost

            # See we are "Dominating"
            if self.retard_needed < -(2/3) * (self.turn+2):
                #Give priority to base upgrade
                if self.resources > self.upgrade_cost:
                    actions.append(upgradeBase())
                    self.resources -= self.upgrade_cost
            else:
                #Buy enough ranged to get more retard
                if 
            
            # Check if retard enough to upgrade base and be safe
        #-----------------------------
        
        # When we have 100 ranges in front of base buy more ranges to the cell over the base
        if self.building_level > 6 and front_base_type in [EMPTY_CELL, ALLIED_SOLDIER_RANGED] and self.resources>=SOLDIER_RANGED_COST and front_base_quant > 0:
            ranges_amount = ((self.resources-SOLDIER_MELEE_COST*5)//SOLDIER_RANGED_COST)
            actions.append(recruitSoldiers(ALLIED_SOLDIER_RANGED, ranges_amount, (1, VCENTER)))
            self.resources -= ranges_amount * SOLDIER_RANGED_COST
            pos = (1, VCENTER)
            to = (1, VCENTER-1)
            amount  = front_base_quant - 0
            actions.append(moveSoldiers(pos, to, amount))

        print(self.board[:,:,0]==ALLIED_SOLDIER_RANGED)

        if self.board[1, VCENTER-1,1]>0:
            pos = (1, VCENTER-1)
            to = (1, VCENTER-2)
            amount = self.board[1, VCENTER - 1, 1]
            if amount>50:
                actions.append(moveSoldiers(pos, to, 50))

        if sum(self.board[self.board[:,:,0]==ALLIED_SOLDIER_RANGED,1]) > 150:
            
            melees_amount = 5
            actions.append(recruitSoldiers(ALLIED_SOLDIER_MELEE, melees_amount, (0, VCENTER+1)))
            self.resources -= melees_amount * SOLDIER_MELEE_COST   
        
        
        #-----------------------------

        #-----------------------------
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

        #-----------------------------
        # ACTIONS
        
        for i in range(len(entities)):
            if entities[i][1][0]==ALLIED_SOLDIER_RANGED:
              moveaction=self.ActionRange(entities[i],flags)
              if moveaction == None:
                  continue
              actions.append(moveaction)
            if entities[i][1][0]==ALLIED_SOLDIER_MELEE:
                moveaction=self.ActionMelee(entities[i],flags)
                if moveaction == None:
                    continue
                actions.append(moveaction)

        playActions(actions)
        self.turn += 1
        self.enemies_next5rounds = []
        #-----------------------------
        
#-------------------------------

#-------------MAIN--------------
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

#-------------------------------