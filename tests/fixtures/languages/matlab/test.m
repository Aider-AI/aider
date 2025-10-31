classdef Person
    properties
        name    (1,1) string
        age     (1,1) double
    end

    methods
        function obj = Person(name, age)
            arguments
                name    (1,1) string
                age     (1,1) double = NaN
            end
            % Constructor for Person class
            obj.name = name;
            obj.age  = age;
        end

        function greeting = greet(obj,formal)
            arguments
                obj
                formal  (1,1) logical = false
            end
            if formal
                prefix = "Good day";
            else
                prefix = "Hello";
            end
            greeting = sprintf("%s, %s!", prefix, obj.name);
        end
    end
end

function greetings = create_greeting_list(people)
    arguments
        people  (1,:) Person
    end
    % Create greetings for a list of people.
    greetings = string(numel(people), 0);
    for i = 1:numel(people)
        greetings(i) = people(i).greet();
    end
end  