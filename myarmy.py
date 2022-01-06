import sys


from actions import *
from utils import *
from utils import _PRINT

import json
import numpy as np


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
        

    def play(self): # agent move, call playActions only ONCE
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

        enemy=np.where(self.board[:,:,0]==ENEMY_SOLDIER_MELEE)
        enemy=[(a,b) for a,b in zip(enemy[0],enemy[1])]
        print(enemy)


        for y in range(HEIGHT):
            for x in range(WIDTH):
                mapcell=self.board[x,y]

        # for r in range(1,4):
        #     origincell = self.board[r, VCENTER]
        #     targetcell = self.board[r+1, VCENTER]
        #     soldier_type, soldier_amount = origincell
        #     if soldier_type in [EMPTY_CELL, origincell[0]] and soldier_amount > 0 :  # if target cell is empty or if contains same type troops
        #         moveaction = moveSoldiers((r, VCENTER), (r+1, VCENTER), soldier_amount)
        #         actions.append(moveaction)


        # example how to move troops from (4,0) to (4,1), step by step
        # origincell = self.board[0][4]   #in case of numpy array would be self.board[4,0]
        # targetcell = self.board[1][4]   #in case of numpy array would be self.board[4,1]
        for r in range(0,5):
            origincell=self.board[4,r]
            targetcell = self.board[4, r+1]
            soldier_type, soldier_amount = origincell
            if soldier_type in [EMPTY_CELL, origincell[0]] and soldier_amount>0:  # if target cell is empty or if contains same type troops
                moveaction = moveSoldiers((4,r),(4,r+1),soldier_amount)
                actions.append(  moveaction )

        for r in range(10,5,-1):
            origincell=self.board[4,r]
            targetcell = self.board[4, r-1]
            soldier_type, soldier_amount = origincell
            if soldier_type in [EMPTY_CELL, origincell[0]] and soldier_amount>0:  # if target cell is empty or if contains same type troops
                moveaction = moveSoldiers((4,r),(4,r-1),soldier_amount)
                actions.append(  moveaction )

        for r in range(0,5):
            origincell=self.board[5,r]
            targetcell = self.board[5, r+1]
            soldier_type, soldier_amount = origincell
            if soldier_type in [EMPTY_CELL, origincell[0]] and soldier_amount>0:  # if target cell is empty or if contains same type troops
                moveaction = moveSoldiers((5,r),(5,r+1),soldier_amount)
                actions.append(  moveaction )

        for r in range(10,5,-1):
            origincell=self.board[5,r]
            targetcell = self.board[5, r-1]
            soldier_type, soldier_amount = origincell
            if soldier_type in [EMPTY_CELL, origincell[0]] and soldier_amount>0:  # if target cell is empty or if contains same type troops
                moveaction = moveSoldiers((5,r),(5,r-1),soldier_amount)
                actions.append(  moveaction )

        playActions(actions)
        

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


