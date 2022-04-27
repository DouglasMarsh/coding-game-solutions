r=x=>readline().split(' '), pr=(c)=>print(c);
[,,,F,P,,,E] = rl().map(Number);
e = Array(E).fill().map(()=>rl()).sort((a,b)=>a[0]-b[0]);
e.push([F,P]);

while (true) {
    const [f, p, d] = rl();
    if(d === 'LEFT' && +e[f][1] > p || d === 'RIGHT' && +e[f][1] < p ) {
        pr('BLOCK');
    } else {
        pr('WAIT');
    }
}


r=x=>readline().split(" ")
i=r()
e=[...Array(+i[7])].map(x=>r()).sort((a,b)=>a[0]-b[0])
e.push([0,i[4]])
w="WAIT"
for(;;){[f,p,d]=r()
if(d=="NONE"){print(w);continue}
c=+e[f][1]
l=d=="LEFT"
print(c<=p&&l||c>=p&&!l?w:"BLOCK")}