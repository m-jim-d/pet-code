#!/usr/bin/env python3

# Filename: A16a_BodyTypes.py

# This file is based on the body_types.py file in the examples directory of the 
# pybox2d distribution. This depends on the pygame framework in that distribution so 
# all the framework files must be in the same directory as this file.

# -*- coding: utf-8 -*-
#
# C++ version Copyright (c) 2006-2007 Erin Catto http://www.box2d.org
# Python version by Ken Lauer / sirkne at gmail dot com
# 
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 1. The origin of this software must not be misrepresented; you must not
# claim that you wrote the original software. If you use this software
# in a product, an acknowledgment in the product documentation would be
# appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
# misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

from math import cos, sin, pi

from Box2D.examples.framework import (Framework, Keys, main)
from Box2D import (b2EdgeShape, b2FixtureDef, b2PolygonShape, b2_dynamicBody,
                   b2_kinematicBody, b2_staticBody, 
                   b2Filter, b2Vec2, b2CircleShape)

                   
class BodyTypes (Framework):
    name = "Body Types, Guns, and Slingshot."
    description = "Change body type keys: (d)dynamic, (s)static, (k)kinematic.\n" + \
                  "Add stuff: (p)pyramid, (r)rectangle, (c)circle.\n" + \
                  "Shoot gun: g or b. b has variable speed based on mouse string.\n" + \
                  "Slingshot: shift and mouse drag."
    speed = 3 # platform speed
    
    def __init__(self):
        super(BodyTypes, self).__init__()

        self.time = 0
        
        # A list for keeping track of the age of the bullets.
        self.bullet_list = []
        
        # Collision masking (also see collision_filtering.py)
        # This positive (+5) non_bullets group index insures collisions in this group. 
        self.non_bullets = 5
        # Categories
        self.gunCategory = 0x0002
        self.bulletCategory = 0x0004
        # Masks
        self.gunMask = 0xFFFF
        # An exclusive OR to keep bullets from colliding with the gun parts.
        self.bulletMask = 0xFFFF ^ self.gunCategory         

        # The ground
        ground = self.world.CreateBody(
                shapes=b2EdgeShape(vertices=[(-30,0),(30,0)]) 
        )

        # The attachment
        attachment_fixture = b2FixtureDef(
                shape=b2PolygonShape( box=(0.5,2)), 
                density=2.0,
                filter = b2Filter(
                    groupIndex = self.non_bullets,
                    categoryBits = self.gunCategory,
                    maskBits = self.gunMask
                )
        )
        
        self.attachment = self.world.CreateDynamicBody(
                position=(0,3), 
                fixtures=attachment_fixture
        )

        # The platform
        fixture = b2FixtureDef(
                shape=b2PolygonShape( box=(4,0.5)), 
                density=2,
                friction=0.6,
                filter = b2Filter(
                    groupIndex = self.non_bullets,
                    categoryBits = self.gunCategory,
                    maskBits = self.gunMask
                )
        )
        
        self.platform=self.world.CreateDynamicBody(
                position=(0,5), 
                fixtures=fixture
        )
        
        # The joints joining the attachment/platform and ground/platform
        self.RJ = self.world.CreateRevoluteJoint(
                bodyA=self.attachment,
                bodyB=self.platform,
                anchor=(0,5),
                maxMotorTorque=50,
                enableMotor=True
        )

        self.PJ = self.world.CreatePrismaticJoint(
                bodyA=ground,
                bodyB=self.platform,
                anchor=(0,5),
                axis=(1,0),
                maxMotorForce = 1000,
                enableMotor = True,
                lowerTranslation = -10,
                upperTranslation = 10,
                enableLimit = True 
        )

    def newpayload(self):
        # Add the payload that initially sits upon the platform in the original demo.
        # Reusing the fixture we previously defined above.
        payload_fixture=b2FixtureDef(
                shape=b2PolygonShape( box=(0.75, 0.75)), 
                density=2,
                friction=0.6,
                filter = b2Filter(
                    groupIndex = self.non_bullets,
                    categoryBits = self.bulletCategory,
                    maskBits = self.bulletMask
                )
        )
        
        self.payload=self.world.CreateDynamicBody(
                position=(0,8), 
                fixtures=payload_fixture,
        )

    def newCircle(self):
        # Some circles for testing contact normals.
        circle_fixture=b2FixtureDef(
                shape=b2CircleShape( radius=2.0), 
                density=2,
                friction=0.6,
                filter = b2Filter(
                    groupIndex = self.non_bullets,
                    categoryBits = self.bulletCategory,
                    maskBits = self.bulletMask
                )
        )
        
        self.circle=self.world.CreateDynamicBody(
                    position=(0,8), 
                    fixtures=circle_fixture,
        ) 
                
    def newpyramid(self):
        # Pyramid on the ground        
        box_half_size = (0.5, 0.5)
        box_density = 5.0
        box_rows = 20

        x=b2Vec2(-27, 0.75)
        deltaX=(0.5625, 1.25)
        deltaY=(1.125, 0)

        for i in range(box_rows):
            y = x.copy()
            for j in range(i, box_rows):
                self.world.CreateDynamicBody(
                    position=y,
                    fixtures=b2FixtureDef(
                            shape=b2PolygonShape(box=box_half_size),
                            density=box_density)
                    )
                y += deltaY
            x += deltaX
                
    def newbullet(self, location_init, angle_radians_init, speed_control):
        # Speed
        v = 30
        
        # Note: angle_degrees = angle_radians_init * 180/pi

        # Scale the bullet speed by the length of the mouse vector.
        if self.mouseJoint and (speed_control == "on"):
            joint_vector = self.mouseJoint.anchorB - self.mouseJoint.target
            
            joint_vector_length = (joint_vector.x**2 + joint_vector.y**2)**0.5
            v = v * joint_vector_length/2.0  # Cut this by a factor of 2...
        
        v_x = v * cos(pi/2- angle_radians_init)
        v_y = v * sin(pi/2- angle_radians_init)        
        
        bullet_fixture = b2FixtureDef(shape=b2PolygonShape(box=(0.25, 0.25)), density=100.0)  #restitution=1.0
        bullet_fixture.filter.groupIndex = 0
        bullet_fixture.filter.categoryBits = self.bulletCategory
        bullet_fixture.filter.maskBits = self.bulletMask
        
        self.bullet=self.world.CreateDynamicBody(
                    position=location_init,
                    bullet=True,
                    fixtures=bullet_fixture,
                    linearVelocity=(v_x, v_y)
                )    
        
        # Put the bullet into a list for clean-up (deletion) later. Tag it with
        # a birth-time stamp so can calculate age later.
        self.bullet_list.append([self.bullet, self.time])
        
    def Keyboard(self, key):
        if key==Keys.K_d:
            self.platform.type=b2_dynamicBody
        elif key==Keys.K_s:
            self.platform.type=b2_staticBody
        elif key==Keys.K_k:
            self.platform.type=b2_kinematicBody
            self.platform.linearVelocity=(-self.speed, 0)
            self.platform.angularVelocity=0
        elif (key==Keys.K_g) or (key==Keys.K_b):
            if (key==Keys.K_b):
                speed_control = "on"
            else:
                speed_control = "off"
            bullet_angle_init = self.RJ.angle
            # Get the world position of the tip (0,2) of the gun barrel.
            bullet_xy_init = self.attachment.transform * (0,2)
            self.newbullet(bullet_xy_init, bullet_angle_init, speed_control)
        elif key==Keys.K_p:
            self.newpyramid()
        elif key==Keys.K_r:
            self.newpayload()
        elif key==Keys.K_c:
            self.newCircle()
            
    def Step(self, settings):
        super(BodyTypes, self).Step(settings)
        
        # Move the platform if it's kinematic.
        if self.platform.type==b2_kinematicBody:
            p = self.platform.transform.position
            if ((p.x < -10) or (p.x > 10)):
                self.platform.linearVelocity *= -1

        # Every step (or second if use commented value), check the age of each bullet in the list.
        self.time += 1.0/60.0
        if (self.stepCount % 1)==0:  # change the 1 to 60 to delay check to every second.
            # Copy the list so you are not deleting in the list used by the for loop.
            bullet_list_copy = self.bullet_list[:]
            for bullet in bullet_list_copy:
                bullet_age = self.time - bullet[1]
                if (bullet_age) > 10.0:
                    # Delete the bullet
                    self.world.DestroyBody(bullet[0])
                    # Delete the sub-list element in the main list.
                    self.bullet_list.remove(bullet)
            # Delete the copy of the list.
            del bullet_list_copy

        
if __name__=="__main__":
     main(BodyTypes)
