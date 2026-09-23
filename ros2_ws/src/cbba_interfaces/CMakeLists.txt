cmake_minimum_required(VERSION 3.8)
project(cbba_interfaces)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Task.msg"
  "msg/TaskArray.msg"
  "msg/CbbaMessage.msg"
  "msg/AgentPlan.msg"
  DEPENDENCIES geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
