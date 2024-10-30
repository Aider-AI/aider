class Car:
    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year
        self.speed = 0

    def accelerate(self, increment):
        self.speed += increment
        print(f"{self.make} {self.model} is now going {self.speed} mph.")

    def brake(self, decrement):
        self.speed = max(0, self.speed - decrement)
        print(f"{self.make} {self.model} slowed down to {self.speed} mph.")

    def honk(self):
        print(f"{self.make} {self.model}: Beep beep!")


class Garage:
    def __init__(self):
        self.cars = []

    def add_car(self, car):
        self.cars.append(car)
        print(f"Added {car.make} {car.model} to the garage.")

    def remove_car(self, car):
        if car in self.cars:
            self.cars.remove(car)
            print(f"Removed {car.make} {car.model} from the garage.")
        else:
            print(f"{car.make} {car.model} is not in the garage.")

    def list_cars(self):
        if self.cars:
            print("Cars in the garage:")
            for car in self.cars:
                print(f"- {car.year} {car.make} {car.model}")
        else:
            print("The garage is empty.")


def main():
    # Create some cars
    car1 = Car("Toyota", "Corolla", 2020)
    car2 = Car("Tesla", "Model 3", 2022)

    # Demonstrate car methods
    car1.accelerate(30)
    car1.honk()
    car1.brake(10)

    # Create a garage and add cars
    my_garage = Garage()
    my_garage.add_car(car1)
    my_garage.add_car(car2)

    # List cars in the garage
    my_garage.list_cars()

    # Remove a car and list again
    my_garage.remove_car(car1)
    my_garage.list_cars()


if __name__ == "__main__":
    main()
