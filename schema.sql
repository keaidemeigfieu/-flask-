-- 新增功能（动态 / 关注 / 通知）所需表结构 + posts 表加 video 列
-- 适用场景：MySQL 里已有 users/posts/replies 三张旧表，需要增量补上。
-- 如果是全新空库，别用这个文件，直接执行 db.create_all() 一次建全即可（更省事、类型绝对一致）。
-- 注意：库和表必须 utf8mb4，否则 emoji 存不进去。

-- 动态表
CREATE TABLE moments (
    id INT NOT NULL AUTO_INCREMENT,
    content TEXT NOT NULL,
    images TEXT,
    video VARCHAR(200),
    created_at DATETIME,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_moments_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 关注表（follower 关注 followed，唯一约束防重复关注）
CREATE TABLE follows (
    id INT NOT NULL AUTO_INCREMENT,
    follower_id INT NOT NULL,
    followed_id INT NOT NULL,
    created_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE KEY uq_follow_pair (follower_id, followed_id),
    CONSTRAINT fk_follows_follower FOREIGN KEY (follower_id) REFERENCES users (id),
    CONSTRAINT fk_follows_followed FOREIGN KEY (followed_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 通知表
CREATE TABLE notifications (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    actor_id INT NOT NULL,
    type VARCHAR(20) NOT NULL,
    target_id INT,
    text VARCHAR(200) NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_notifications_actor FOREIGN KEY (actor_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- posts 表增加视频字段
ALTER TABLE posts ADD COLUMN video VARCHAR(200);
