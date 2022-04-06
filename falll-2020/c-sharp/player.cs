using System;
using System.Linq;
using System.IO;
using System.Text;
using System.Collections;
using System.Diagnostics;
using System.Collections.Generic;

/**
 * Auto-generated code below aims at helping you parse
 * the standard input according to the problem statement.
 **/
class Player
{
    static Stopwatch sw = new Stopwatch();
    class Action
    {

        public int ActionId {get; }
        public string ActionType {get; }        
        public int Delta0 { get; }
        public int Delta1 { get;  }
        public int Delta2 { get;  }
        public int Delta3 { get; }
        public int Price {get; }
        public int TomeIndex {get; }
        public int TaxCount {get;  }
        public bool Castable {get; set;}
        public bool Repeatable {get; }

        
        public double CurrentCost(int inv0, int inv1, int inv2, int inv3)
        {
            // cost is what is consumed (negative Deltas.)
            // current cost is consumption reduced by current inventory
            return Delta3 < 0 ? (Delta3 + inv3) * 4 : 0
                + Delta2 < 0 ? (Delta2 + inv2) * 3 : 0
                + Delta1 < 0 ? (Delta1 + inv1) * 2 : 0
                + Delta0 < 0 ? (Delta0 + inv0) * 1 : 0;
        }
        public double CurrentCost(GameState gs) => CurrentCost(gs.Inv0, gs.Inv1, gs.Inv2, gs.Inv3);

        public Action( string[] inputs )
        {
            ActionId = int.Parse(inputs[0]); // the unique ID of this spell or recipe
            ActionType = inputs[1]; // in the first league: BREW; later: CAST, OPPONENT_CAST, LEARN, BREW
            Delta0 = int.Parse(inputs[2]); // tier-0 ingredient change
            Delta1 = int.Parse(inputs[3]); // tier-1 ingredient change
            Delta2 = int.Parse(inputs[4]); // tier-2 ingredient change
            Delta3 = int.Parse(inputs[5]); // tier-3 ingredient change
            Price = int.Parse(inputs[6]); // the price in rupees if this is a potion
            TomeIndex = int.Parse(inputs[7]); // in the first two leagues: always 0; later: the index in the tome if this is a tome spell, equal to the read-ahead tax; For brews, this is the value of the current urgency bonus
            TaxCount = int.Parse(inputs[8]); // in the first two leagues: always 0; later: the amount of taxed tier-0 ingredients you gain from learning this spell; For brews, this is how many times you can still gain an urgency bonus
            Castable = inputs[9] != "0"; // in the first league: always 0; later: 1 if this is a castable player spell
            Repeatable = inputs[10] != "0"; // for the first two leagues: always 0; later: 1 if this is a repeatable player spell
        
            // Calculate a Price for Spells
            if( ActionType != "BREW")
            {
                // price is what is produced
                Price = Delta3 > 0 ? Delta3 * 4 : 0
                    + Delta2 > 0 ? Delta2 * 3 : 0
                    + Delta1 > 0 ? Delta1 * 2 : 0
                    + Delta0 > 0 ? Delta0 * 1 : 0;
            }

        }
        
        private Action( Action a)
        {
            ActionId = a.ActionId;
            ActionType = a.ActionType;
            Delta0 = a.Delta0;
            Delta1 = a.Delta1;
            Delta2 = a.Delta2;
            Delta3 = a.Delta3;
            Price = a.Price;
            TomeIndex = a.TomeIndex;
            TaxCount = a.TaxCount;
            Castable = a.Castable;
            Repeatable = a.Repeatable;
        }
        public Action Clone() => new Action( this );
        public bool CanCast(int inv0, int inv1, int inv2, int inv3)
        {
            if( ActionType == "BREW" || (ActionType == "CAST" && Castable))
            {
                var delta = new[]
                {
                    inv0 + Delta0,
                    inv1 + Delta1,
                    inv2 + Delta2,
                    inv3 + Delta3,
                };
                return !delta.Any(i => i < 0 )
                    && delta.Sum(i => i) <= 10;
            }

            return false;
        }
        public bool CanCast(GameState s) => CanCast(s.Inv0, s.Inv1, s.Inv2, s.Inv3);
        public bool FullfillsNeed( int[] need )
        {
            return (need[0] < 0 && Delta0 > 0)
                || (need[1] < 0 && Delta1 > 0) 
                || (need[2] < 0 && Delta2 > 0) 
                || (need[3] < 0 && Delta3 > 0);
        }
        public override string ToString()
        {
            return $"{ActionType} {ActionId}";
        }
    }
    
    class GameState
    {

        public int ActionCount => Actions.Count;
        public Dictionary<int, Action> Actions {get;}
        public List<Action> Potions {get;}
        public List<Action> Spells {get;}
        public List<Action> OpSpells {get;}
        public int Inv0 {get; set; }
        public int Inv1 {get; set; }
        public int Inv2 {get; set; }
        public int Inv3 {get; set; }
        public int Score {get; set;}

        public int OpInv0 {get; set; }
        public int OpInv1 {get; set; }
        public int OpInv2 {get; set; }
        public int OpInv3 {get; set; }
        public int OpScore {get; set;}


        public int BrewCount {get; private set;}
        public int Turn {get; set;}

        public bool GameEnd => BrewCount >= 3 || Turn >= 100;

        private GameState(){}
        public GameState(int turn)
        {
           
            Actions = new Dictionary<int, Action>();
            Potions = new List<Action>();
            Spells = new List<Action>();
            OpSpells = new List<Action>();

            Turn = turn;
        }
        private GameState(GameState parent): this()
        {
            
            foreach(var a in parent.Actions.Values)
            {
                this.AddAction( a.Clone() );
            }
            this.Inv0 = parent.Inv0;
            this.Inv1 = parent.Inv1;
            this.Inv2 = parent.Inv2;
            this.Inv3 = parent.Inv3;
            this.Score = parent.Score;

            this.OpInv0 = parent.OpInv0;
            this.OpInv1 = parent.OpInv1;
            this.OpInv2 = parent.OpInv2;
            this.OpInv3 = parent.OpInv3;
            this.OpScore = parent.OpScore;

            this.BrewCount = parent.BrewCount;
            this.Turn = parent.Turn;
            
        }
        
        public GameState Clone() => new GameState( this );
        
        public Action AddAction(Action a)
        {
            Actions.Add(a.ActionId, a);
            switch (a.ActionType)
            {
                case "BREW":
                    Potions.Add(a);
                    break;
                case "CAST":
                    Spells.Add(a);
                    break;
                case "OPPONENT_CAST":
                    OpSpells.Add(a);
                    break;
            }

            return a;
        }
        
        public GameState PlayTurn(string actionType, int? actionId)
        {
            var newState = this.Clone();
            newState.Turn = this.Turn +1;

            if( actionType == "WAIT") return newState;

            if( actionType == "REST")
            {
                newState.Spells.ForEach( s => s.Castable = true);
                return newState;
            }

            var action = newState.Actions[ actionId.Value ];
            newState.Inv0 += action.Delta0;
            newState.Inv1 += action.Delta1;
            newState.Inv2 += action.Delta2;
            newState.Inv3 += action.Delta3;

            if( actionType == "BREW")
            {
                newState.Actions.Remove( actionId.Value );
                newState.Potions.Remove( action );

                newState.Score += action.Price;
                newState.BrewCount = this.BrewCount +1;

            }
            else
            {
                action.Castable = false;
            }

            return newState;
        }       
        public GameState PlayTurn(Action a) => PlayTurn(a.ActionType, a.ActionId);
        public bool CanPlay(string actionType, int? actionId = null)
        {
            if( actionType == "WAIT") return true;
            if( actionType == "REST")
            {
                return this.Spells.Any( s => s.Castable == false);
            }
            
            
            var action = this.Actions[ actionId.Value];
            return action.CanCast(Inv0, Inv1, Inv2, Inv3);
        }
        public bool CanPlay(Action a) => CanPlay(a.ActionType, a.ActionId);
        
        public Action BestPotionToTarget()
        {
            return Potions.OrderBy(p => p.Price / p.CurrentCost( this) ).First();
        }
    }
    
    static void Main(string[] args)
    {
        sw.Restart();
        int turn = 0;
        List<Action> recipe = null;
        Action targetPotion = null;
        // game loop
        while (true)
        {
            turn += 1;
            Console.Error.WriteLine($"Start Turn[{turn}]: {sw.ElapsedMilliseconds}");
            Console.Error.WriteLine($"Start Parse: Turn[{turn}]: {sw.ElapsedMilliseconds}");
            
            var gamestate = new GameState( turn );
            gamestate.Turn = turn;

            int actionCount = int.Parse(Console.ReadLine());
            for (int i = 0; i < actionCount; i++)
            {
                var action = new Action( Console.ReadLine().Split(' ') );
                gamestate.AddAction( action );
            }
            
            var inputs = Console.ReadLine().Split(' ');
            gamestate.Inv0 = int.Parse(inputs[0]);
            gamestate.Inv1 = int.Parse(inputs[1]);
            gamestate.Inv2 = int.Parse(inputs[2]);
            gamestate.Inv3 = int.Parse(inputs[3]);
            gamestate.Score = int.Parse(inputs[4]);

            inputs = Console.ReadLine().Split(' ');
            gamestate.OpInv0 = int.Parse(inputs[0]);
            gamestate.OpInv1 = int.Parse(inputs[1]);
            gamestate.OpInv2 = int.Parse(inputs[2]);
            gamestate.OpInv3 = int.Parse(inputs[3]);
            gamestate.OpScore = int.Parse(inputs[4]);

            Console.Error.WriteLine($"End Parse: Turn[{turn}]: {sw.ElapsedMilliseconds}");

            string actionToPlay = "WAIT";

            Console.Error.WriteLine($"Begin Determine Target: Turn[{turn}]: {sw.ElapsedMilliseconds}");
            var bestTarget = gamestate.BestPotionToTarget();
            Console.Error.WriteLine($"End Determine Target {bestTarget.ActionId}: Turn[{turn}]: {sw.ElapsedMilliseconds}");
            
            if( bestTarget.ActionId != targetPotion?.ActionId)
            {
                targetPotion = bestTarget;
                Console.Error.WriteLine($"Begin Determine Target {bestTarget.ActionId} Recipe: Turn[{turn}]: {sw.ElapsedMilliseconds}");
            
                recipe = GetRecipe(gamestate, bestTarget);
                Console.Error.WriteLine($"End Determine Target {bestTarget.ActionId} Recipe: Turn[{turn}]: {sw.ElapsedMilliseconds}");
                Console.Error.WriteLine($"    Recipe:{ string.Join(";", recipe) }");
            }

            var nextAction = recipe.FirstOrDefault(a => gamestate.CanPlay(a));
            if( nextAction == null )
            {
                if( gamestate.Spells.Any(s => !s.Castable))
                {
                    actionToPlay = "REST";
                }
            }

                      
            
            // Write an action using Console.WriteLine()
            // To debug: Console.Error.WriteLine("Debug messages...");

            Console.WriteLine( nextAction?.ToString() ?? actionToPlay );
            sw.Restart();
        }
    }
    static List<Action> GetRecipe(GameState state, Action potion)
    {
        var recipe = new List<Action>( new[] { potion });

        var delta = new[] { 
            state.Inv0 + potion.Delta0,
            state.Inv1 + potion.Delta1,
            state.Inv2 + potion.Delta2,
            state.Inv3 + potion.Delta3,
        };

        var spells = state.Spells.OrderBy(s => s.Price / s.CurrentCost( state ));
        while( delta.Any(i => i < 0))
        {
            var spell = spells.First(s => s.FullfillsNeed( delta) );
            recipe.Add(spell);

            delta[0] += spell.Delta0;
            delta[1] += spell.Delta1;
            delta[2] += spell.Delta2;
            delta[3] += spell.Delta3;
        }

        return recipe;
    }
    
}