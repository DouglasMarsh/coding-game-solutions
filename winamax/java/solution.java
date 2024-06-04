import java.util.*;
import java.util.Map.Entry;
import java.io.*;
import java.math.*;

class Directions {
    public static final Set<Character> ALL = Set.of('^','v','<','>');
    public static final Map<Character,Set<Character>> ExclusionMap = Map.of(
            '^', Set.of('^','<','>'),
            'v', Set.of('v','<','>'),
            '<', Set.of('^','v','<'),
            '>', Set.of('^','v','>'));
}

class HitResult {
    public char landed;
    public Ball ball;

    public HitResult(int h, int w, int d, char l) {
        landed = l;
        ball = new Ball(h,w,d);
    }
}
class Ball {
    int height;
    int width;
    int shotCount;

    public Ball(int h, int w, int c) {
        height = h;
        width = w;
        shotCount = c;
    }


    public int getHeight() {
        return height;
    }
    public int getWidth() {
        return width;
    }
    public int getShotCount() {
        return shotCount;
    }

    @Override
    public String toString() {
        return "Ball(%s,%s:%s)".formatted(height, width, shotCount);
    }
    public void getPotentialSolutions(
            Course c, String hiTstory, List<String> solutions, Set<Character> directions) {
        for(char d: directions) {
            HitResult r = quickHit(c, d);
            if( r != null ) {
                if( r.landed == 'H'){
                    solutions.add( hiTstory + d );
                } else {
                    r.ball.getPotentialSolutions(c, hiTstory + d, solutions, Directions.ExclusionMap.get(d));
                }
            }
        }
    }
    public HitResult quickHit(Course c, char direction) {
        int eHeight = height;
        int eWidth = width;

        switch(direction) {
            case '^':
                eHeight = getHeight() - getShotCount();
                break;
            case 'v':
                eHeight = getHeight() + getShotCount();
                break;
            case '<':
                eWidth = getWidth() - getShotCount();
                break;
            case '>':
                eWidth = getWidth() + getShotCount();
                break;
        }

        //System.err.printf("Hit %s in dir %s to land at %s,%s ", this, direction, eHeight, eWidth);

        // make sure ball isn't out of bounds
        if( eHeight < 0 || eHeight >= c.getHeight() || eWidth < 0 || eWidth >= c.getWidth()) {
            //System.err.println(" out of bounds");
            return null;
        }

        int h = height;
        int w = width;
        switch(direction) {
            case '^':
                for( --h; h > eHeight; h--){
                    char crossed = c.getCell(h,w);
                    if( crossed == 'H') {
                        return new HitResult(h, w, 0, 'H');
                    }
                    if( crossed != '.' && crossed != 'X') {
                        return null;
                    }
                }
                break;

            case 'v':
                for( ++h; h < eHeight; h++){
                    char crossed = c.getCell(h,w);
                    if( crossed == 'H') {
                        return new HitResult(h, w, 0, 'H');
                    }
                    if( crossed != '.' && crossed != 'X') {
                        return null;
                    }
                }
                break;
            case '<':
                for( --w; w > eWidth; w--){
                    char crossed = c.getCell(h,w);
                    if( crossed == 'H') {
                        return new HitResult(h, w, 0, 'H');
                    }
                    if( crossed != '.' && crossed != 'X') {
                        return null;
                    }
                }
                break;
            case '>':
                for( ++w; w < eWidth; w++){
                    char crossed = c.getCell(h,w);
                    if( crossed == 'H') {
                        return new HitResult(h, w, 0, 'H');
                    }
                    if( crossed != '.' && crossed != 'X') {
                        return null;
                    }
                }
                break;
            default:
                throw new Error("Unknown direction %s".formatted( direction ));
        }



        char landed = c.getCell(eHeight, eWidth);

        //System.err.printf("on %s%n", landed);

        // must land on grass or Hole
        if( landed != '.' && landed != 'H') {
            return null;
        }

        var result = new HitResult(eHeight, eWidth, shotCount -1, landed);

        // final shot MUST land in hole
        if( shotCount == 1 &&  landed != 'H'){
            return null;
        }

        return result;
    }

}
class Course {

    char[][] grid;

    public Course(int h, int w) {
        grid = new char[h][w];
    }
    public Course(Course c) {
        grid = new char[c.getHeight()][c.getWidth()];
        for(int h = 0; h < getHeight(); h++) {
            for( int w = 0; w < getWidth(); w++) {
                setCell(h,w, c.getCell(h, w));
            }
        }
    }


    public char getCell(int h, int w) {
        if( h < 0 || h >= grid.length ) return '*';
        if( w < 0 || w >= grid[0].length ) return '*';

        return grid[h][w];
    }
    public void setCell(int h, int w, char c) {
        grid[h][w] = c;
    }
    public void setRow(int h, String row) {
        for(int w = 0; w < row.length(); w++) {
            setCell(h, w, row.charAt(w));
        }
    }
    public int getHeight() {
        if( grid == null ) return 0;
        return grid.length;
    }
    public int getWidth() {
        if( grid == null ) return 0;
        return grid[0].length;
    }
    public boolean cellIsWaterOrGrass(int h, int w) {
        char cell = getCell(h,w);
        return cell == 'X' || cell == '.';
    }

    public Course clone() {
        return new Course(this);
    }
    public void play() {

        Map<Ball, List<String>> ballSolutions = new HashMap<>();
        Ball b = findBall();
        while( b != null ){

            System.err.printf("found %s%n", b);

            var solutions = new ArrayList<String>();
            b.getPotentialSolutions(this,"", solutions, Directions.ALL);
            if( solutions.size() == 1){

                System.err.printf("%s had a single solution%n", b);
                if( !this.applySolution(b, solutions.get(0)) ){
                    throw new Error("unable to apply solution %s, %s".formatted(b, solutions.get(0)));
                }

                this.writeCourse(System.err);

            } else {
                System.err.printf("%s has multiple solutions%n", b);
                solutions.sort(Comparator.comparingInt(String::length));
                for(String s: solutions) {
                    System.err.println(s);
                }
                ballSolutions.put(b, solutions);

                this.setCell(b.getHeight(), b.getWidth(), '0');
            }
            b = findBall();
        }

        if( ballSolutions.isEmpty() ) {
            System.err.println("All balls had a single solution");
            this.writeSolution(System.out);
            return;
        }

        System.err.println("Resolving balls with multiple solutions");

        Course solution = resolveSolutions(ballSolutions.entrySet().stream().toList(), 0);
        solution.writeSolution(System.out);
    }
    public void writeCourse(PrintStream out) {

        for (char[] chars : grid) {
            for (char c : chars) {
                out.print(c);
            }
            out.println();
        }
    }
    public void writeSolution(PrintStream out) {

        for (char[] chars : grid) {
            for (char c : chars) {
                if (!Directions.ALL.contains(c)) {
                    out.print('.');
                } else {
                    out.print(c);
                }
            }
            out.println();
        }
    }

    Ball findBall() {
        for(int h = 0; h < getHeight(); h++) {
            for( int w = 0; w < getWidth(); w++) {
                char cell = getCell(h,w);
                if( Character.isDigit( cell ) && Character.getNumericValue(cell) > 0 ) {
                    return new Ball(h, w, Character.getNumericValue(cell));
                }
            }
        }

        return null;
    }

    Course resolveSolutions(List<Entry<Ball,List<String>>> solutions, int index) {
        if( index < solutions.size() ){
            var bSolution = solutions.get(index);
            for(String solution : bSolution.getValue()) {
                Course updated = this.clone();
                if( updated.applySolution(bSolution.getKey(), solution) ) {
                    Course candidate = updated.resolveSolutions( solutions, index+1 );
                    if( candidate != null ) return candidate;
                }
            }

            return null;
        }
        return this;

    }

    boolean applySolution(Ball b, String solution) {
        int height = b.getHeight();
        int width = b.getWidth();

        int dist = b.getShotCount();

        for(char direction : solution.toCharArray()) {
            int eHeight = height;
            int eWidth = width;

            // update cell where ball begins
            this.setCell(eHeight,eWidth, direction);

            switch(direction) {
                case '^':
                    for( --eHeight ; eHeight > height - dist; eHeight--){
                        if( this.getCell(height,width) == 'H') {
                            this.setCell(eHeight, eWidth, '0');
                            break;
                        }
                        if( !this.cellIsWaterOrGrass(eHeight, eWidth)) return false;

                        this.setCell(eHeight,eWidth, direction);
                    }
                    break;

                case 'v':
                    for( ++eHeight ; eHeight < height + dist; eHeight++){
                        if( this.getCell(height,width) == 'H') {
                            this.setCell(eHeight, eWidth, '0');
                            break;
                        }
                        if( !this.cellIsWaterOrGrass(eHeight, eWidth)) return false;

                        this.setCell(eHeight,eWidth, direction);
                    }
                    break;
                case '<':
                    for(--eWidth; eWidth > width - dist; eWidth--){
                        if( this.getCell(height,width) == 'H') {
                            this.setCell(eHeight, eWidth, '0');
                            break;
                        }
                        if( !this.cellIsWaterOrGrass(eHeight, eWidth)) return false;

                        this.setCell(eHeight,eWidth, direction);
                    }
                    break;
                case '>':
                    for(++eWidth; eWidth < width + dist; eWidth++){
                        if( this.getCell(height,width) == 'H') {
                            this.setCell(eHeight, eWidth, '0');
                            break;
                        }
                        if( !this.cellIsWaterOrGrass(eHeight, eWidth)) return false;

                        this.setCell(eHeight,eWidth, direction);

                    }
                    break;
                default:
                    throw new Error("Unknown direction %s".formatted( direction ));
            }

            height = eHeight;
            width = eWidth;
            dist --;


        }

        char landed = this.getCell(height,width);
        if( landed != '0' && landed != 'H') {
            System.err.printf("%s,%s is %s instead of H %n", height, width, landed);
            return false;
        }

        this.setCell(height, width, '0');
        return true;
    }
}

class Solution {
    public static void main(String args[]) {
        Scanner in = new Scanner(System.in);
        int width = in.nextInt();
        int height = in.nextInt();

        System.err.printf("%s,%s%n", width, height);

        Course course = new Course(height, width);

        for (int h = 0; h < height; h++) {
            String row = in.next();
            course.setRow(h, row );

            System.err.printf("%s%n", row);
        }
        in.close();
        System.err.println();

        course.play();
    }
}