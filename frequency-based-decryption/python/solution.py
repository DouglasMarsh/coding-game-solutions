import sys
import math
import re
import string

UPPER_CASE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWER_CASE = 'abcdefghijklmnopqrstuvwxyz'

alpha_freq_xref = [
  ( 0.0808, 'A'),
  ( 0.0167, 'B'),
  ( 0.0318, 'C'),
  ( 0.0399, 'D'),
  ( 0.1256, 'E'),
  ( 0.0217, 'F'),
  ( 0.0180, 'G'),
  ( 0.0527, 'H'),
  ( 0.0724, 'I'),
  ( 0.0014, 'J'),
  ( 0.0063, 'K'),
  ( 0.0404, 'L'),
  ( 0.0260, 'M'),
  ( 0.0738, 'N'),
  ( 0.0747, 'O'),
  ( 0.0191, 'P'),
  ( 0.0009, 'Q'),
  ( 0.0642, 'R'),
  ( 0.0659, 'S'),
  ( 0.0915, 'T'),
  ( 0.0279, 'U'),
  ( 0.0100, 'V'),
  ( 0.0189, 'W'),
  ( 0.0021, 'X'),
  ( 0.0165, 'Y'),
  ( 0.0007, 'Z'),
]
alpha_freq_xref.sort(key=lambda tup: tup[0], reverse=True)

def reshift(seed, msg):
    shifted = ''
    for c in msg:
        if ord(c) >= 65 and ord(c) <= 90:
            alphabet = UPPER_CASE
        elif ord(c) >= 97 and ord(c) <= 122:
            alphabet = LOWER_CASE
        else:
            shifted += c
            continue
    
        idx = alphabet.index(c)
        idx -= seed
        
        while idx < 0 :
            idx = idx + 26

        shifted += alphabet[idx]

    return shifted

def validate(msg):
    print(f'Validating msg: {msg}', file=sys.stderr, flush=True)

    words = [word.strip(string.punctuation) for word in msg.split() if word.strip(string.punctuation).isalpha()]

    
    print(f'Validating words: {words}', file=sys.stderr, flush=True)

    for w in words:
        if len(w) == 1:
            if w.upper() != 'I' and w.upper() != 'A':
                print(f'Word: {w} is not valid. Not I or A', file=sys.stderr, flush=True)
                return False
        
        
         
        if re.search('[AEIOUY]', w.upper()) == None:
            if w != 'Mr' and w != 'Mrs' and w != 'Dr':
                print(f'Word: {w} is not valid. No vowels', file=sys.stderr, flush=True)
                return False 
        
    
    return True

def main():
    message = input()
    print(f'Encoded message: {message}', file=sys.stderr, flush=True)

    normalized_message = re.sub('[^A-Z]+', '', message.upper())
    print(f'Normalized message: {normalized_message}', file=sys.stderr, flush=True)


    encode_freq_dict = {}
    for c in normalized_message:        
        encode_freq_dict[c] =  encode_freq_dict.setdefault(c, 0) +1
    
    encode_freq_xref = [(k, v) for k, v in encode_freq_dict.items()]
    encode_freq_xref.sort(key=lambda tup: tup[1], reverse=True)
     
    print(f'Encoded frequency map: {encode_freq_xref}', file=sys.stderr, flush=True)

       
    most_frequent = encode_freq_xref[0][0]
    for alpha in alpha_freq_xref:
        key = ord(most_frequent) - ord(alpha[1])
        if key < 0:
            key += 26

        print(f'Calculated key: {key}', file=sys.stderr, flush=True)
        decoded = reshift(key, message)
        if validate( decoded ):
            print(decoded)
        return

    print("UNABLE TO DECODE")

main()