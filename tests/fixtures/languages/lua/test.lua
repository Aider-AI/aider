-- Simple Lua module with a greeting function

-- Person class definition
local Person = {}
Person.__index = Person

function Person.new(name)
    local self = setmetatable({}, Person)
    self.name = name
    return self
end

-- Main greeting function to be detected by ctags
function greet(person)
    return "Hello, " .. person.name .. "!"
end

-- Example usage
local p = Person.new("World")
print(greet(p))

return {
    Person = Person,
    greet = greet
}
