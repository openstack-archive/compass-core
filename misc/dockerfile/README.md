Building compass images.

NOCONFIG
*In the directory of the dockerfile
The image has to be tagged as compass:noconfig*

docker build --tag="compass:noconfig" .

CONFIG
*In the directory of the dockerfile
The image should be tagged as compass:config
Remember to modify compass.conf and the .chef folder as needed.*

docker build --tag="compass:config" .

Building cobbler images.

NOCONFIG
*In the directory of the dockerfile
The image has to be tagged as cobbler:noconfig*

docker build --tag="cobbler:noconfig" .

CONFIG
*In the directory of the dockerfile
The image should be tagged as cobbler:config
Remember to modify the cobbler.conf as needed.*

docker build --tag="cobbler:config" .


RUNNING Cobbler

*Cobbler must be run before the compass container.*
It may take a while to download everything and configure the cobbler server correctly.

There runner scripts in the runners folder.
They assume cobbler config image is tagged as "cobbler:config"

cobbler.sh creates a detached container will all ports published.

cobblerLinked.sh is cobbler.sh but also names the container cobblerlink

cobblerLinkedExposed.sh is cobblerLinked.sh but pubblished port 80 of the container to 8080 on the host.

cobblerLinkedExposedInteractive.sh is cobblerLinkedExposed.sh but not detached.


RUNNING Compass
*Compass must be run after cobbler and compass.conf and knife.rb must be configured properly*
/it will not build otherwise/

There are runner scripts in the runners folder.

compass.sh created a detached compass container.

compassLinkCobbler.sh is compass.sh but creates a link between the containers if they are on the *same host*
Must be passed the name/container id of the cobbler container.

NODAMONCompassLinkCobbler.sh is compassLinkCobbler.sh but not detached.
