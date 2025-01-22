#!/usr/bin/env python3

# Filename: A09_2D_vector_class_testing.py

from A09_vec2d import Vec2D

vec_a = Vec2D(1, 2)
vec_b = Vec2D(-3, 0)
print()
print("vec_a =", vec_a)
print("vec_b =", vec_b)

print()
projection_of_a_on_b = vec_a.projection_onto(vec_b)
print("projection of a onto b (a's parallel component) =", projection_of_a_on_b)

print()
print("a's perpendicular component (via projection onto a rotated version of b) =", vec_a.projection_onto( vec_b.rotated(90)))
print("a's perpendicular component (by subtraction from the original a) =", vec_a - projection_of_a_on_b)

print()
print("vec_a / 2 =", vec_a / 2.0)

print()
print("vec_a * 2 =", vec_a * 2.0)

print()
print("vec_a + vec_b =", vec_a + vec_b)

print()
print("vec_a - vec_b =", vec_a - vec_b)

print()
print("vec_a.length() =", vec_a.length())

print("vec_a.rotated(15) =", vec_a.rotated(15))
print("vec_a.rotated(15).length() =", vec_a.rotated(15).length())
print("vec_a.rotated(16).length() =", vec_a.rotated(16).length())
print("vec_a.rotated(17).length() =", vec_a.rotated(17).length())
print("vec_a.rotated(25).length() =", vec_a.rotated(25).length())

print()
print()
print("Vec2D(0.0,1.0).rotate90 =", Vec2D(0.0,1.0).rotate90())
print()
print("Vec2D(0.0,1.0).get_angle() = ", Vec2D(0.0,1.0).get_angle())
print()
print("Vec2D(0.0,1.0).set_angle( 45.0) =", Vec2D(0.0,1.0).set_angle( 45.0))
print()
print("Vec2D(0.0,1.0).get_angle_between(Vec2D(1.0,0.0)) =", Vec2D(0.0,1.0).get_angle_between(Vec2D(1.0,0.0)))
print()
print("Vec2D(0.0,1.0).get_angle_between(Vec2D(1.0,1.0)) =", Vec2D(0.0,1.0).get_angle_between(Vec2D(1.0,1.0)))
print()

vec_a *= -1.0
print("running vec_a *= -1.0, gives vec_a =", vec_a)
