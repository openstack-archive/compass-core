tests
=======

To run these tests, compass/tests is needed,
.testr.conf in compass-core needs to be modified: change 
test_command=OS_STDOUT_CAPTURE=1 OS_STDERR_CAPTURE=1 ${PYTHON:-python} -m subunit.run discover -t ./ ./compass/tests $LISTOPT $IDOPTION to 
test_command=OS_STDOUT_CAPTURE=1 OS_STDERR_CAPTURE=1 ${PYTHON:-python} -m subunit.run discover -t ./ ./ $LISTOPT $IDOPTION
The test_chef_installer needs libcrypto.so 


