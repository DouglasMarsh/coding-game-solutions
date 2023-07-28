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
class skynet_revolution_1
{
    static void Main(string[] args)
    {
        string[] inputs;
        inputs = Console.ReadLine().Split(' ');
        int N = int.Parse(inputs[0]); // the total number of nodes in the level, including the gateways
        int L = int.Parse(inputs[1]); // the number of links
        int E = int.Parse(inputs[2]); // the number of exit gateways

        var graph = new Graph();
        var gateWays = new int[E];

        for (int i = 0; i < L; i++)
        {
            inputs = Console.ReadLine().Split(' ');
            int N1 = int.Parse(inputs[0]); // N1 and N2 defines a link between these nodes
            int N2 = int.Parse(inputs[1]);

            graph.AddLink(N1, N2);
        }
        for (int i = 0; i < E; i++)
        {
            int EI = int.Parse(Console.ReadLine()); // the index of a gateway node
            gateWays[i] = EI;
        }

        // game loop
        while (true)
        {
            int SI = int.Parse(Console.ReadLine()); // The index of the node on which the Skynet agent is positioned this turn
            var paths = new List<IEnumerable<int>>();
            foreach( var gate in gateWays )
            {
                paths.Add(graph.ShortestPath(gate, SI));
            }
            IEnumerable<int> sPath = paths.OrderBy(p => p.Count()).First();

            Console.WriteLine("{0} {1}", sPath.First(), sPath.Skip(1).First());
        }
    }

    class Graph : Dictionary<int, HashSet<int>>
    {
        public void AddLink(int n1, int n2)
        {
            if (!ContainsKey(n1)) Add(n1, new HashSet<int>());
            this[n1].Add(n2);

            if (!ContainsKey(n2)) Add(n2, new HashSet<int>());
            this[n2].Add(n1);
        }
        public void RemoveLink(int n1, int n2)
        {
            if (ContainsKey(n1)) this[n1].Remove(n2);
            if (ContainsKey(n2)) this[n2].Remove(n1);
        }
        
        public IEnumerable<int> ShortestPath(int start, int end)
        {
            var previous = new Dictionary<int, int>();

            var queue = new Queue<int>();
            queue.Enqueue(start);

            while (queue.Count > 0)
            {
                var node = queue.Dequeue();
                foreach (var neighbor in this[node])
                {
                    if (previous.ContainsKey(neighbor))
                        continue;

                    previous[neighbor] = node;
                    if( neighbor == end )
                    {
                        queue.Clear();
                        break;
                    }
                    queue.Enqueue(neighbor);
                }
            }

            var path = new List<int> { };

            var current = end;
            while (!current.Equals(start))
            {
                path.Add(current);
                current = previous[current];
            };

            path.Add(start);
            path.Reverse();

            return path;
        }
    }
}
