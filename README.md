The `unitysync` script provides a simple form of local package management for use with the [Unity3D](https://unity3d.com/) game engine. It allows the configuration of folders in your main project that will be synched with external dependency projects on the same machine.

To use the script you need to clone your product dependencies to somewhere on your machine, and then configure the dependencies in a `depend.json` file in the root of your main project.

Changes in the dependency project can be pulled using the `pull` command, and changes in the main project can be pushed back to the dependency project using the `push` command.

