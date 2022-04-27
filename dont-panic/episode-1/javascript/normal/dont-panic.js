/**
 * Auto-generated code below aims at helping you parse
 * the standard input according to the problem statement.
 **/

var inputs = readline().split(' ');
const nbFloors = parseInt(inputs[0]); // number of floors
const width = parseInt(inputs[1]); // width of the area
const nbRounds = parseInt(inputs[2]); // maximum number of rounds
const exitFloor = parseInt(inputs[3]); // floor on which the exit is found
const exitPos = parseInt(inputs[4]); // position of the exit on its floor
const nbTotalClones = parseInt(inputs[5]); // number of generated clones
const nbAdditionalElevators = parseInt(inputs[6]); // ignore (always zero)
const nbElevators = parseInt(inputs[7]); // number of elevators

var exits = new Array(nbFloors);
exits[exitFloor]=exitPos;
for (let i = 0; i < nbElevators; i++) {
    inputs = readline().split(' ');
    const elevatorFloor = parseInt(inputs[0]); // floor on which this elevator is found
    const elevatorPos = parseInt(inputs[1]); // position of the elevator on its floor
    exits[elevatorFloor] = elevatorPos;
}
console.error( JSON.stringify(exits) );
// game loop
while (true) {
    var inputs = readline().split(' ');
    const cloneFloor = parseInt(inputs[0]); // floor of the leading clone
    const clonePos = parseInt(inputs[1]); // position of the leading clone on its floor
    const direction = inputs[2]; // direction of the leading clone: LEFT or RIGHT

    // Write an action using console.log()
    // To debug: console.error('Debug messages...');

    if (cloneFloor == -1)
        console.log("WAIT");
    else {
        var vector = clonePos - exits[cloneFloor];
        console.error(direction + ": " + vector);
        if ( (direction == "LEFT") == (vector < 0) && vector != 0)
            console.log("BLOCK");
        else
            console.log("WAIT"); // action: WAIT or BLOCK
    }

}


// lets simplify this readline / split junk
r=x=>readline().split(" ")
// lets read all the static input data
// 0: don't care, 1: don't care, 2: don't care
// 3: exit floor, 4: exit pos, 5: don't care, 6: don't care
// 7: n of elevators
d=r()
// lets fill dem elevators (0: floor, 1: elevator position)
// since they come unsorted in some test cases.. lets add ugly sorting
f=[...Array(+d[7])].map(x=>r()).sort((a,b)=>a[0]-b[0])
// lets add the exit as elevator.. cause.. why differentiate?
// until here i dont care about floors anymore since floors are represented by the array index now.
f.push([0,d[4]])
// this is just to reduce the amount of used characters:
w="WAIT"
// x = 0: floor of leading clone, 1: position of leading clone, 2: direction of leading clone (LEFT, RIGHT)
for(;;){x=r()
// if there is no leading clone, continue to the next iteration
if(x[2]=="NONE"){print(w);continue}
// lets grab the position of the exit / elevator of the current leading clone
c=+f[x[0]][1]
// figure out if the leading clone is headed left
l=x[2]=="LEFT"
// if the exit / elevator is in direction to where the leading clone is directing -> wait, else block
print(c<=x[1]&&l||c>=x[1]&&!l?w:"BLOCK")}

// thanks for reading.
// feel free to tell me that i'm a horrible coder and that nobody should code in this style at work.