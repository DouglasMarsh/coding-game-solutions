import sys
import math

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def reshift(seed, msg):
    shifted = ''
    for c in msg:
        idx = alphabet.index(c)
        idx -= seed
        
        while idx < 0 :
            idx = idx + 26

        shifted += alphabet[idx]
        seed += 1

    return shifted
def shift(seed, msg):
    shifted = ''
    for c in msg:
        idx = alphabet.index(c)
        idx += seed
        
        while idx > 25 :
            idx = idx - 26

        shifted += alphabet[idx]
        seed += 1

    return shifted

def apply(encoder, msg):
    result = ""
    for c in msg:
        result += encoder.get(c)
    
    return result

def encode(seed, encoders, message):
    
    result = shift(seed, message)    
    result1 = apply(encoders[0], result )    
    result2 = apply(encoders[1], result1 )
    result3 = apply(encoders[2], result2 )

    return result3

def decode(seed, decoders, result3):    
    result2 = apply(decoders[2], result3 )
    result1 = apply(decoders[1], result2 )
    result = apply(decoders[0], result1 ) 
    message = reshift(seed, result)

    return message

def main():

    encoders = []
    decoders = []

    operation = input()
    seed = int(input())

    for i in range(3):
        rotor = input()
        encoders.append({x:y for x,y in zip( alphabet, rotor )})
        decoders.append({x:y for x,y in zip( rotor, alphabet )})

    message = input()

    encMsg = encode( seed, encoders, message )
    decMsg = decode(seed, decoders, encMsg )

    print(f"Message: { message }", file=sys.stderr, flush=True)
    print(f"Encoded: { encMsg }", file=sys.stderr, flush=True)
    print(f"Decoded: { decMsg }", file=sys.stderr, flush=True)

    if operation == "ENCODE":
        print( encode( seed, encoders, message ))
    else :        
        print( decode( seed, decoders, message ))



# Write an answer using print
# To debug: print("Debug messages...", file=sys.stderr, flush=True)

main()
