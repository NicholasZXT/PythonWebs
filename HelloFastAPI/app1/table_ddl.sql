/*
 Navicat Premium Data Transfer

 Source Server         : MySQL-Local
 Source Server Type    : MySQL
 Source Server Version : 80031
 Source Host           : localhost:3306
 Source Schema         : hello_fastapi

 Target Server Type    : MySQL
 Target Server Version : 80031
 File Encoding         : 65001

 Date: 19/09/2023 16:34:00
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `uid` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `gender` varchar(16) DEFAULT NULL,
  PRIMARY KEY (`uid`) USING BTREE,
  INDEX `ix_users_uid`(`uid`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='FastAPI-用户测试表';

-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO `users` VALUES (1, 'xiaoming', 'male');
INSERT INTO `users` VALUES (2, 'xiaohong', 'female');
INSERT INTO `users` VALUES (3, 'xiaohua', 'male');
INSERT INTO `users` VALUES (4, 'daniel', 'male');
INSERT INTO `users` VALUES (5, 'jane', 'female');

SET FOREIGN_KEY_CHECKS = 1;

