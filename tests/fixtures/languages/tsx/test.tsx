import React, { useState, useEffect } from 'react';

interface UserProps {
    name: string;
    age?: number;
}

// Component with props interface
const UserGreeting: React.FC<UserProps> = ({ name, age }) => {
    const [greeting, setGreeting] = useState<string>('');

    useEffect(() => {
        setGreeting(`Hello, ${name}${age ? ` (${age})` : ''}!`);
    }, [name, age]);

    return <h1>{greeting}</h1>;
};

// Custom hook
function useCounter(initial: number = 0) {
    const [count, setCount] = useState(initial);
    const increment = () => setCount(c => c + 1);
    return { count, increment };
}

// Constants
const DEFAULT_NAME = 'World';
const MAX_AGE = 150;

export { UserGreeting, useCounter, DEFAULT_NAME, MAX_AGE };
