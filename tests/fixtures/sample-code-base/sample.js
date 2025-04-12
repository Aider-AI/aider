// Sample JavaScript script with 7 functions

// 1. A simple greeting function
function greet(name) {
    return `Hello, ${name}!`;
}

// 2. A function to calculate the area of a circle
function calculateCircleArea(radius) {
    return Math.PI * radius * radius;
}

// 3. A function to check if a number is prime
function isPrime(number) {
    if (number <= 1) return false;
    for (let i = 2; i <= Math.sqrt(number); i++) {
        if (number % i === 0) return false;
    }
    return true;
}

// 4. A function to reverse a string
function reverseString(str) {
    return str.split('').reverse().join('');
}

// 5. A function to generate a random number within a range
function getRandomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// 6. A function to filter out even numbers from an array
function filterEvenNumbers(numbers) {
    return numbers.filter(num => num % 2 !== 0);
}

// 7. A function to calculate the factorial of a number
function factorial(n) {
    if (n === 0 || n === 1) return 1;
    return n * factorial(n - 1);
}

// Example usage
console.log(greet("Alice"));
console.log(calculateCircleArea(5));
console.log(isPrime(17));
console.log(reverseString("JavaScript"));
console.log(getRandomNumber(1, 100));
console.log(filterEvenNumbers([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
console.log(factorial(5));
