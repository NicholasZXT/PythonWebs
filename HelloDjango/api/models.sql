/*
 Navicat Premium Data Transfer

 Source Server         : MySQL-Local
 Source Server Type    : MySQL
 Source Server Version : 80031
 Source Host           : localhost:3306
 Source Schema         : hello_django

 Target Server Type    : MySQL
 Target Server Version : 80031
 File Encoding         : 65001

 Date: 01/08/2023 11:09:41
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for api_student
-- ----------------------------
DROP TABLE IF EXISTS `api_student`;
CREATE TABLE `api_student`  (
  `sid` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `gender` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `grade` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `grade_class` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `create_date` date NOT NULL,
  PRIMARY KEY (`sid`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_student
-- ----------------------------
INSERT INTO `api_student` VALUES (101, '张三', '男', '六年级', '3班', '2023-09-01');
INSERT INTO `api_student` VALUES (102, '小明', '男', '五年级', '1班', '2023-09-01');
INSERT INTO `api_student` VALUES (103, '小红', '女', '4年级', '2班', '2023-09-01');


-- ----------------------------
-- Table structure for api_teacher
-- ----------------------------
DROP TABLE IF EXISTS `api_teacher`;
CREATE TABLE `api_teacher`  (
  `tid` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `gender` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `subject` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `grade` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `grade_class` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `create_date` date NOT NULL,
  PRIMARY KEY (`tid`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_teacher
-- ----------------------------
INSERT INTO `api_teacher` VALUES (201, '周老师', '女', '政治', '六年级', '3班', '2023-07-01');
INSERT INTO `api_teacher` VALUES (202, '张老师', '男', '数学', '六年级', '3班', '2023-07-01');

SET FOREIGN_KEY_CHECKS = 1;
