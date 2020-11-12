# Stacks

Stacks is a collection of python utilties to setup a pacman build system.

It is not an end to end product but more like a support library for you to write your own systems quickly with a gui (i.e the configuration is also done in python).

However, almost everything is abstracted away from the user, who just needs to define where the pacman PKGBUILD files are, the job scheduler, and what workers there are.

I currently use the build system personally to automatically rebuild some packages for me whenver upstream versions come in. It has some features which are unmatched
among other build systems.

 * Dependency checks. If the dependencies of a library haven't been built yet, neither will it.
 * Directly uses libalpm via the python bindings to determine what packages are already in the binary repository.
 * Direct PKGBUILD dependency/metadata extraction into python objects
 * Nice web gui where you can see all the queues and logs (and can save history to a history.json file upon server exit)
 * Automatic time-based requeueing of failed builds.

This is not meant to be a commercial-quality software build stack. It just offers a lightweight web gui (no interaction, meaning you can't manually requeue, unfortunately) and tight integration with pacman.
