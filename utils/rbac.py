"""
基于角色的访问控制 (RBAC) 模块

提供角色定义、权限检查和RBAC相关功能
"""
from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from fastapi import HTTPException, status


class Permission(str, Enum):
    """权限枚举"""

    # 通用权限
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

    # Agent相关
    AGENT_USE = "agent:use"
    AGENT_MANAGE = "agent:manage"
    AGENT_CONFIGURE = "agent:configure"

    # 工具相关
    TOOL_EXECUTE = "tool:execute"
    TOOL_DANGEROUS = "tool:dangerous"
    TOOL_MANAGE = "tool:manage"

    # 项目相关
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_SHARE = "project:share"

    # 文件系统相关
    FILE_UPLOAD = "file:upload"
    FILE_READ = "file:read"
    FILE_UPDATE = "file:update"
    FILE_DELETE = "file:delete"
    FILE_SHARE = "file:share"

    # 工作流相关
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"

    # 知识库相关
    KNOWLEDGE_CREATE = "knowledge:create"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_UPDATE = "knowledge:update"
    KNOWLEDGE_DELETE = "knowledge:delete"

    # 用户管理相关
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # 系统管理相关
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_ADMIN = "system:admin"

    # 通知相关
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_SEND = "notification:send"

    # 反馈相关
    FEEDBACK_SUBMIT = "feedback:submit"
    FEEDBACK_VIEW = "feedback:view"
    FEEDBACK_MANAGE = "feedback:manage"


class Role(str, Enum):
    """角色枚举"""

    ADMIN = "admin"            # 系统管理员
    USER = "user"              # 普通用户
    GUEST = "guest"            # 访客
    OPERATOR = "operator"      # 运营人员
    DEVELOPER = "developer"     # 开发者
    ANALYST = "analyst"        # 分析师


@dataclass
class RoleDefinition:
    """角色定义"""
    name: Role
    display_name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    is_system_role: bool = True  # 是否系统角色（不可删除）


# 预定义角色及其权限
ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.ADMIN: RoleDefinition(
        name=Role.ADMIN,
        display_name="系统管理员",
        description="拥有所有权限，可管理整个系统",
        permissions={p for p in Permission},  # 所有权限
        is_system_role=True
    ),

    Role.DEVELOPER: RoleDefinition(
        name=Role.DEVELOPER,
        display_name="开发者",
        description="可以开发和配置系统功能",
        permissions={
            # Agent权限
            Permission.AGENT_USE,
            Permission.AGENT_CONFIGURE,
            Permission.TOOL_EXECUTE,
            Permission.TOOL_DANGEROUS,
            Permission.TOOL_MANAGE,

            # 项目权限
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_DELETE,

            # 文件权限
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
            Permission.FILE_UPDATE,
            Permission.FILE_DELETE,

            # 工作流权限
            Permission.WORKFLOW_CREATE,
            Permission.WORKFLOW_READ,
            Permission.WORKFLOW_UPDATE,
            Permission.WORKFLOW_DELETE,
            Permission.WORKFLOW_EXECUTE,

            # 知识库权限
            Permission.KNOWLEDGE_CREATE,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_UPDATE,
            Permission.KNOWLEDGE_DELETE,

            # 系统权限
            Permission.SYSTEM_CONFIG,
            Permission.SYSTEM_MONITOR,

            # 通知权限
            Permission.NOTIFICATION_READ,
            Permission.NOTIFICATION_SEND,
        },
        is_system_role=True
    ),

    Role.OPERATOR: RoleDefinition(
        name=Role.OPERATOR,
        display_name="运营人员",
        description="负责日常运营和内容管理",
        permissions={
            # Agent权限
            Permission.AGENT_USE,
            Permission.TOOL_EXECUTE,
            Permission.TOOL_DANGEROUS,

            # 项目权限
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_UPDATE,

            # 文件权限
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
            Permission.FILE_UPDATE,

            # 工作流权限
            Permission.WORKFLOW_CREATE,
            Permission.WORKFLOW_READ,
            Permission.WORKFLOW_UPDATE,
            Permission.WORKFLOW_EXECUTE,

            # 知识库权限
            Permission.KNOWLEDGE_CREATE,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_UPDATE,

            # 反馈权限
            Permission.FEEDBACK_VIEW,
            Permission.FEEDBACK_MANAGE,

            # 通知权限
            Permission.NOTIFICATION_READ,
            Permission.NOTIFICATION_SEND,
        },
        is_system_role=True
    ),

    Role.ANALYST: RoleDefinition(
        name=Role.ANALYST,
        display_name="分析师",
        description="查看系统统计数据和报告",
        permissions={
            # 只读权限
            Permission.PROJECT_READ,
            Permission.FILE_READ,
            Permission.WORKFLOW_READ,
            Permission.KNOWLEDGE_READ,
            Permission.SYSTEM_MONITOR,
            Permission.NOTIFICATION_READ,
            Permission.FEEDBACK_VIEW,
        },
        is_system_role=True
    ),

    Role.USER: RoleDefinition(
        name=Role.USER,
        display_name="普通用户",
        description="标准用户，使用基本功能",
        permissions={
            # 基础权限
            Permission.AGENT_USE,
            Permission.TOOL_EXECUTE,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_UPDATE,
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
            Permission.FILE_UPDATE,
            Permission.WORKFLOW_CREATE,
            Permission.WORKFLOW_READ,
            Permission.WORKFLOW_EXECUTE,
            Permission.KNOWLEDGE_CREATE,
            Permission.KNOWLEDGE_READ,
            Permission.NOTIFICATION_READ,
            Permission.FEEDBACK_SUBMIT,
        },
        is_system_role=True
    ),

    Role.GUEST: RoleDefinition(
        name=Role.GUEST,
        display_name="访客",
        description="只读访客，查看公开内容",
        permissions={
            Permission.READ,
            Permission.PROJECT_READ,
            Permission.FILE_READ,
            Permission.KNOWLEDGE_READ,
        },
        is_system_role=True
    ),
}


class RBACChecker:
    """RBAC权限检查器"""

    @staticmethod
    def get_role_permissions(role: Role) -> Set[Permission]:
        """
        获取角色的所有权限

        Args:
            role: 角色

        Returns:
            Set[Permission]: 权限集合
        """
        role_def = ROLE_DEFINITIONS.get(role)
        if not role_def:
            return set()
        return role_def.permissions

    @staticmethod
    def role_has_permission(role: Role, permission: Permission) -> bool:
        """
        检查角色是否拥有指定权限

        Args:
            role: 角色
            permission: 权限

        Returns:
            bool: 是否有权限
        """
        return permission in RBACChecker.get_role_permissions(role)

    @staticmethod
    def user_has_permission(user_roles: List[Role], permission: Permission) -> bool:
        """
        检查用户是否拥有指定权限（用户可能有多个角色）

        Args:
            user_roles: 用户角色列表
            permission: 权限

        Returns:
            bool: 是否有权限
        """
        for role in user_roles:
            if RBACChecker.role_has_permission(role, permission):
                return True
        return False

    @staticmethod
    def check_permission(user_roles: List[Role], required_permission: Permission) -> None:
        """
        检查权限，如果没有权限则抛出异常

        Args:
            user_roles: 用户角色列表
            required_permission: 需要的权限

        Raises:
            HTTPException: 如果没有权限
        """
        if not RBACChecker.user_has_permission(user_roles, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {required_permission.value}"
            )

    @staticmethod
    def check_any_permission(user_roles: List[Role], required_permissions: List[Permission]) -> None:
        """
        检查是否拥有任一所需权限

        Args:
            user_roles: 用户角色列表
            required_permissions: 需要的权限列表（满足任一即可）

        Raises:
            HTTPException: 如果没有任何权限
        """
        for permission in required_permissions:
            if RBACChecker.user_has_permission(user_roles, permission):
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required one of: {[p.value for p in required_permissions]}"
        )

    @staticmethod
    def check_all_permissions(user_roles: List[Role], required_permissions: List[Permission]) -> None:
        """
        检查是否拥有所有所需权限

        Args:
            user_roles: 用户角色列表
            required_permissions: 需要的权限列表（需要全部满足）

        Raises:
            HTTPException: 如果缺少任何权限
        """
        for permission in required_permissions:
            RBACChecker.check_permission(user_roles, permission)

    @staticmethod
    def get_role_definition(role: Role) -> Optional[RoleDefinition]:
        """
        获取角色定义

        Args:
            role: 角色

        Returns:
            RoleDefinition: 角色定义或None
        """
        return ROLE_DEFINITIONS.get(role)

    @staticmethod
    def list_all_roles() -> List[Dict[str, any]]:
        """
        列出所有角色

        Returns:
            List[Dict]: 角色信息列表
        """
        return [
            {
                "name": role.value,
                "display_name": defn.display_name,
                "description": defn.description,
                "permissions": [p.value for p in defn.permissions],
                "is_system_role": defn.is_system_role
            }
            for role, defn in ROLE_DEFINITIONS.items()
        ]

    @staticmethod
    def get_permissions_for_roles(roles: List[Role]) -> Set[Permission]:
        """
        获取多个角色的所有权限（去重）

        Args:
            roles: 角色列表

        Returns:
            Set[Permission]: 权限集合
        """
        all_permissions = set()
        for role in roles:
            all_permissions.update(RBACChecker.get_role_permissions(role))
        return all_permissions


# 便捷函数
def require_role(*roles: Role):
    """
    装饰器工厂：要求用户拥有指定角色之一

    Usage:
        @require_role(Role.ADMIN, Role.DEVELOPER)
        async def admin_function(user: UserAuthInfo = Depends(get_current_user)):
            ...
    """
    from functools import wraps
    from utils.jwt_auth import get_current_user

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里需要从依赖注入获取当前用户
            # 实际使用时需要配合FastAPI的Depends
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(*permissions: Permission):
    """
    装饰器工厂：要求用户拥有指定权限之一

    Usage:
        @require_permission(Permission.USER_CREATE, Permission.USER_UPDATE)
        async def user_management():
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 实际使用时需要从上下文获取用户角色
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 初始化
def init_rbac():
    """初始化RBAC系统"""
    from utils.logger import get_logger
    logger = get_logger("RBAC")
    logger.info("✅ RBAC系统初始化完成")
    logger.info(f"   角色数量: {len(ROLE_DEFINITIONS)}")
    logger.info(f"   权限数量: {len(Permission)}")
    logger.info("   预定义角色: " + ", ".join([r.value for r in Role]))
