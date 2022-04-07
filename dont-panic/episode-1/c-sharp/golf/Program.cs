using System;
using System.Linq;
class D{
static void Main(string[] args){
Func<string,int> p=(string s)=>int.Parse(s);
Func<string[]> r=()=>Console.ReadLine().Split();
Func<int[]> y=()=>r().Select(i=>p(i)).ToArray();
var l=y();var s=new int[l[0]];
s[l[3]]=l[4];
for(int i=0;i++<l[7];){ var m=y();s[m[0]]=m[1];}
while(true){var d = r();
int f=p(d[0]);int t=p(d[1]);var z=d[2][0];var c="WAIT";
if(z!='N'&&s[f]!=t){var n=s[f]-t>0?'R':'L';if(n!=z&&t!=s[Math.Max(0,f-1)])c="BLOCK";}
Console.WriteLine(c);}}}