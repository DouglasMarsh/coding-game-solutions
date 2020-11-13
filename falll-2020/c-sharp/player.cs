using System;
using System.Linq;
using System.IO;
using System.Text;
using System.Collections;
using System.Collections.Generic;

/**
 * Auto-generated code below aims at helping you parse
 * the standard input according to the problem statement.
 **/
class Player
{
    class Inventory
    {
        public int[] Ingredients {get; set;}
        public int Score {get; set; }

        public Inventory(string[] inputs)
        {
            Ingredients = new[] {
                int.Parse(inputs[0]), // tier-0 ingredient change
                int.Parse(inputs[1]), // tier-1 ingredient change
                int.Parse(inputs[2]), // tier-2 ingredient change
                int.Parse(inputs[3]), // tier-3 ingredient change
            };
            Score = int.Parse(inputs[4]); // amount of rupees
        }

        public bool CanFulfill( ClientOrder o)
        {
            // canBrew
            var ingredients = o.Ingredients;
            for( int i = 0; i < ingredients.Length; i++)
            {
                if( Ingredients[i] < ingredients[i]) return false;
            }

            return true;
        }
    }
    class ClientOrder
    {
        public int ActionId {get; set;}
        public string ActionType {get; set;}
        public int[] Ingredients {get; set;}
        public int Price {get; set;}
        public int TomeIndex {get; set;}
        public int TaxCount {get; set; }
        public bool Castable {get; set;}
        public bool Repeatable {get; set;}

        public ClientOrder( string[] inputs )
        {
            ActionId = int.Parse(inputs[0]); // the unique ID of this spell or recipe
            ActionType = inputs[1]; // in the first league: BREW; later: CAST, OPPONENT_CAST, LEARN, BREW
            Ingredients = new[] {
                int.Parse(inputs[2]), // tier-0 ingredient change
                int.Parse(inputs[3]), // tier-1 ingredient change
                int.Parse(inputs[4]), // tier-2 ingredient change
                int.Parse(inputs[5]), // tier-3 ingredient change
            };
            Price = int.Parse(inputs[6]); // the price in rupees if this is a potion
            TomeIndex = int.Parse(inputs[7]); // in the first two leagues: always 0; later: the index in the tome if this is a tome spell, equal to the read-ahead tax; For brews, this is the value of the current urgency bonus
            TaxCount = int.Parse(inputs[8]); // in the first two leagues: always 0; later: the amount of taxed tier-0 ingredients you gain from learning this spell; For brews, this is how many times you can still gain an urgency bonus
            Castable = inputs[9] != "0"; // in the first league: always 0; later: 1 if this is a castable player spell
            Repeatable = inputs[10] != "0"; // for the first two leagues: always 0; later: 1 if this is a repeatable player spell
        }
        
        public override string ToString()
        {
            return $"{ActionType} {ActionId}";
        }
    }
    static void Main(string[] args)
    {
        string[] inputs;

        // game loop
        while (true)
        {
            var clientOrders = new List<ClientOrder>();

            int actionCount = int.Parse(Console.ReadLine()); // the number of spells and recipes in play
            for (int i = 0; i < actionCount; i++)
            {
                inputs = Console.ReadLine().Split(' ');
                clientOrders.Add( new ClientOrder( inputs ));
            }

            inputs = Console.ReadLine().Split(' ');
            var playerInventory = new Inventory( inputs );

            inputs = Console.ReadLine().Split(' ');
            var opponentInventory = new Inventory( inputs );

            clientOrders = clientOrders.OrderByDescending( o => o.Price).ToList();

            var orderToFill = clientOrders.FirstOrDefault( o => playerInventory.CanFulfill(o));

            // Write an action using Console.WriteLine()
            // To debug: Console.Error.WriteLine("Debug messages...");


            // in the first league: BREW <id> | WAIT; later: BREW <id> | CAST <id> [<times>] | LEARN <id> | REST | WAIT
            Console.WriteLine( orderToFill?.ToString() ?? "WAIT" );
        }
    }
}