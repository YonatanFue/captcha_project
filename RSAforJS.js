class RSAEncryption {
    static RSA_Encryption(msg) {
        const pow = 17;  // public exponent
        const mod = 3233;  // modulus
        let encrypted = "";

        for (let c of msg) {
            let a = this.Char_To_Ascii(c);
            encrypted += String.fromCharCode(this.Pow_Mod(a, pow, mod));
        }
        return encrypted;
    }

    static Pow_Mod(a, x, n) {
        const xbits = this.Num_To_Bit(x);
        let y = 1;
        for (let bit of xbits) {
            y = (y * y) % n;
            if (bit === '1') {
                y = (a * y) % n;
            }
        }
        return y;
    }

    static Num_To_Bit(num) {
        let result = '';
        let quotient = num;
        while (quotient > 0) {
            const m = quotient % 2;
            quotient = Math.floor(quotient / 2);
            result += m.toString();
        }
        return result.split('').reverse().join('');
    }

    static Char_To_Ascii(char) {
        return char.charCodeAt(0);
    }
}
