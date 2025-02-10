import asyncio
import numpy as np
from gymnasium.spaces import Box, Space
from stable_baselines3 import A2C
from stable_baselines3.common.vec_env import DummyVecEnv
from poke_env.environment.abstract_battle import AbstractBattle
from poke_env.player import (
    RandomPlayer,
    ObsType
)
from poke_env.player.battle_order import BattleOrder, ForfeitBattleOrder, DoubleBattleOrder
from poke_env.player.env_player import EnvPlayer
from poke_env.player.player import Player
from poke_env.data import GenData
from MaxDamgPlayer import MaxDamagePlayer
from SmartBot import SmartBot
type_chart = GenData(9).type_chart
team1 = """
Archaludon @ Assault Vest  
Ability: Stamina  
Level: 50  
Tera Type: Fairy  
EVs: 220 HP / 4 Def / 52 SpA / 116 SpD / 116 Spe  
Bold Nature  
IVs: 26 Atk  
- Electro Shot  
- Draco Meteor  
- Flash Cannon  
- Body Press  

Rillaboom @ Loaded Dice  
Ability: Grassy Surge  
Level: 50  
Tera Type: Fire  
EVs: 204 HP / 116 Atk / 4 Def / 60 SpD / 124 Spe  
Adamant Nature  
- Bullet Seed  
- Grassy Glide  
- Fake Out  
- High Horsepower  

Basculegion @ Choice Band  
Ability: Swift Swim  
Level: 50  
Tera Type: Grass  
EVs: 252 Atk / 4 Def / 252 Spe  
Adamant Nature  
- Wave Crash  
- Last Respects  
- Protect  
- Aqua Jet  

Kingambit @ Black Glasses  
Ability: Defiant  
Level: 50  
Tera Type: Dark  
EVs: 236 HP / 228 Atk / 4 Def / 4 SpD / 36 Spe  
Adamant Nature  
- Kowtow Cleave  
- Sucker Punch  
- Swords Dance  
- Protect  

Pelipper @ Focus Sash  
Ability: Drizzle  
Level: 50  
Tera Type: Ghost  
EVs: 4 HP / 252 SpA / 252 Spe  
Modest Nature  
- Weather Ball  
- Hurricane  
- Tailwind  
- Protect  

Electabuzz @ Eviolite  
Ability: Vital Spirit  
Level: 50  
Tera Type: Ghost  
EVs: 244 HP / 180 Def / 4 SpA / 20 SpD / 60 Spe  
Bold Nature  
IVs: 20 Atk  
- Electroweb  
- Taunt  
- Follow Me  
- Protect 
"""
class Gen9VGCEnvDoublePlayer(EnvPlayer):
    _ACTION_SPACE = list(range(784))  # 28 actions for each Pokémon → 28 * 28 = 784
    _DEFAULT_BATTLE_FORMAT = "gen9vgc2024regh"

    def action_to_move(self, action: int, battle: AbstractBattle) -> BattleOrder:
        """
        Converts actions to move orders for Double Battle with Terastallization.

        The conversion is done as follows:

        action = -1:
            The battle will be forfeited.
        0 <= action < 784:
            Action is split into two parts:
                - first_action: action // 28 → Action for Pokémon 1
                - second_action: action % 28 → Action for Pokémon 2

            Pokémon Action Breakdown (0-27):
                0  <= action < 12:
                    Normal move (0-3) targeting (Opponent 1, Opponent 2, Ally).
                12 <= action < 24:
                    Terastallized move (0-3) targeting (Opponent 1, Opponent 2, Ally).
                24 <= action < 28:
                    Switch action (0-3).

        If the proposed action is illegal, a random legal move is performed.
        """
        if action == -1:
            return ForfeitBattleOrder()

        first_action = action // 28
        second_action = action % 28

        if battle.active_pokemon[0] == None or battle.active_pokemon[1] == None and len(battle.available_switches[0]) > 0:
            return Player.choose_random_move(battle)
        
        def map_action(pokemon_action, available_moves, battle, tera, can_switch):
            if pokemon_action < 12:  # Normal Move
                move_id = pokemon_action // 3
                target_id = pokemon_action % 3
                if move_id < len(available_moves):
                    return Player.create_order(available_moves[move_id],
                         move_target=target_id - 1 )
                
            elif 12 <= pokemon_action < 24:  # Terastallized Move
                move_id = (pokemon_action - 12) // 3
                target_id = (pokemon_action - 12) % 3
                if move_id < len(available_moves) and tera:
                    return Player.create_order(available_moves[move_id],
                         terastallize=True, move_target = target_id)
                elif move_id < len(available_moves):
                    return Player.create_order(available_moves[move_id],
                         terastallize=False, move_target = target_id)
                
            elif 24 <= pokemon_action < 28:  # Switch
                switch_id = pokemon_action - 24
                if switch_id < len(can_switch):
                    return Player.create_order(can_switch[switch_id])
            return None
        
#        print("="*50+
#              "\nBattle Detail",
#              "\nPokemon = ", battle.active_pokemon,
#              "\nAction = ", action, first_action, second_action,
#              "\nBattle Move = ", battle.available_moves,
#              "\nPokemon 1 Move = ", battle.available_moves[0],
#              "\nPokemon 2 Move = ", battle.available_moves[1],
#              "\nSwitch = ", battle.available_switches[0],
#              "\nTera = ", battle.can_tera,
#              "\n"+"="*50)
        
#        print("Action 1 start...")
        action_1 = map_action(first_action, battle.available_moves[0], battle, battle.can_tera[0],
                              battle.available_switches[0])
#        print("Action 1 is ",action_1 ,"\nAction 2 start...")
        action_2 = map_action(second_action, battle.available_moves[1], battle, battle.can_tera[-1],
                              battle.available_switches[1])
#        print("Action 2 is ",action_2)

        if str(action_1) == str(action_2) and ("switch" in str(action_1)):
            rand_move = Player.choose_random_move(battle)
#            print("Random Move...\n",rand_move)
            return rand_move
        
#       print(str(DoubleBattleOrder(action_1, action_2)))
        if action_1 is None or action_2 is None:
            rand_move = Player.choose_random_move(battle)
#            print("Random Move...\n",rand_move)
            return rand_move
        
#        print("="*50+
#              "\nFinal Action",
#              "\n= ",DoubleBattleOrder(action_1, action_2),
#              "\n"+"="*50)
        
        return DoubleBattleOrder(action_1, action_2)
    
class SimpleRLPlayer(Gen9VGCEnvDoublePlayer):
    def calc_reward(self, battle, last_state) -> float:
        return self.reward_computing_helper(
            battle, fainted_value=2.0, hp_value=1.0, victory_value=30.0
        )

    def embed_battle(self, battle: AbstractBattle) -> ObsType:
        # Moves of Pokémon 1 and Pokémon 2
        moves_p1 = -np.ones(4)
        moves_p2 = -np.ones(4)

        # Multipliers of Pokémon 1's moves against both enemies
        multipliers_p1_e1 = np.ones(4)
        multipliers_p1_e2 = np.ones(4)

        # Multipliers of Pokémon 2's moves against both enemies
        multipliers_p2_e1 = np.ones(4)
        multipliers_p2_e2 = np.ones(4)

        # Get available moves for Pokémon 1
        for i, move in enumerate(battle.available_moves[0]):
            moves_p1[i] = move.base_power / 100
            if move.type:
                if battle.opponent_active_pokemon[0] is not None:
                    multipliers_p1_e1[i] = move.type.damage_multiplier(
                        battle.opponent_active_pokemon[0].type_1,
                        battle.opponent_active_pokemon[0].type_2,
                        type_chart=type_chart
                    )
                else:
                    multipliers_p1_e1[i] = -1

                if battle.opponent_active_pokemon[1] is not None:
                    multipliers_p1_e2[i] = move.type.damage_multiplier(
                        battle.opponent_active_pokemon[1].type_1,
                        battle.opponent_active_pokemon[1].type_2,
                        type_chart=type_chart
                    )
                else:
                    multipliers_p1_e2[i] = -1

        # Get available moves for Pokémon 2
        for i, move in enumerate(battle.available_moves[1]):
            moves_p2[i] = (move.base_power / 100)
            if move.type:
                if battle.opponent_active_pokemon[0] is not None:
                    multipliers_p2_e1[i] = move.type.damage_multiplier(
                        battle.opponent_active_pokemon[0].type_1,
                        battle.opponent_active_pokemon[0].type_2,
                        type_chart=type_chart
                    )
                else:
                    multipliers_p2_e1[i] = -1

                if battle.opponent_active_pokemon[1] is not None:
                    multipliers_p2_e2[i] = move.type.damage_multiplier(
                        battle.opponent_active_pokemon[1].type_1,
                        battle.opponent_active_pokemon[1].type_2,
                        type_chart=type_chart
                    )
                else:
                    multipliers_p2_e2[i] = -1
        # print("="*50,"\n",battle.weather,"\n"+"="*50)
        # Weather condition
        weather = 0
        #if battle.weather:
        #    weather = {
        #        "SUNNYDAY": 1,
        #        "RAINDANCE": 2,
        #        "SANDSTORM": 3,
        #        "SNOW": 4,
        #    }.get(battle.weather, 0)

        # Fainted Pokémon
        fainted_ally = len([mon for mon in battle.team.values() if mon.fainted]) / 4
        fainted_enemy = len([mon for mon in battle.opponent_team.values() if mon.fainted]) / 4

        tera = 1
        if battle.can_tera[0] == False:
            tera = 0

        # Final embedding vector
        final_vector = np.concatenate(
            [
                moves_p1,
                moves_p2,
                multipliers_p1_e1,
                multipliers_p1_e2,
                multipliers_p2_e1,
                multipliers_p2_e2,
                [weather, fainted_ally, fainted_enemy, tera],
            ]
        )
        return final_vector.astype(np.float32)

    def describe_embedding(self) -> Space:
        low = [-1] * 24 + [0, 0, 0, 0]
        high = [3] * 24 + [4, 1, 1, 1]
        return Box(
            np.array(low, dtype=np.float32),
            np.array(high, dtype=np.float32),
            dtype=np.float32,
        )
    
NB_TRAINING_STEPS = 1_000_000
GEN_9_DATA = GenData.from_gen(9)

async def main():
    # Create training and evaluation environments
    random_opponent = RandomPlayer(team=team1,
                                   battle_format="gen9vgc2024regh")
    env_player = SimpleRLPlayer(battle_format="gen9vgc2024regh",
                                team=team1, opponent=random_opponent, start_challenging=True)

    env = DummyVecEnv([lambda: env_player])
    # Create the A2C model using the MLP policy (this is a simple neural network architecture)
    model = A2C("MlpPolicy", env, verbose=1)
    # Training the model
    model.learn(total_timesteps=NB_TRAINING_STEPS)
    print("Training complete.")

    model.save("RL_gen9vgcRH_v10")
    print("Model saved to a2c_gen9vgc_model")

    obs, _ = env_player.reset()
    done = False
    
    while not done:
        try:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env_player.step(action)

            if done:
#                print("Battle finished. Resetting...")
                break 
            
        except RuntimeError as e:
            print(f"Error detected: {e}")
            break  # ป้องกันการ crash ถ้า Battle จบโดยไม่คาดคิด
if __name__ == "__main__":
    asyncio.run(main())
